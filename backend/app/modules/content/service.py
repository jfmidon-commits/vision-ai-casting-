"""
ContentService - Serviço de gerenciamento de Conteúdo Social.

Responsável por:
- Criar e gerenciar itens de conteúdo
- Controlar estados do workflow (draft -> generated -> waiting_approval -> approved -> published)
- Agendar publicações
"""

from typing import Dict, List, Any, Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models import ContentItem
from app.core.event_bus import emit_event, VisionEventType
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ContentService:
    """Serviço de gerenciamento de Conteúdo Social."""

    async def create_content(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        profile_id: UUID,
        content_type: str,  # PHOTO, CAROUSEL, REEL, STORY, PORTFOLIO_UPDATE
        title: Optional[str] = None,
        description: Optional[str] = None,
        caption: Optional[str] = None,
        media_urls: Optional[List[str]] = None,
        hashtags: Optional[List[str]] = None,
        platform: str = "instagram",
        metadata: Optional[Dict] = None,
    ) -> ContentItem:
        """Cria um novo item de conteúdo."""
        content = ContentItem(
            tenant_id=tenant_id,
            profile_id=profile_id,
            content_type=content_type,
            title=title,
            description=description,
            caption=caption,
            media_urls=media_urls or [],
            hashtags=hashtags or [],
            platform=platform,
            status="draft",
            metadata=metadata or {},
        )

        db.add(content)
        await db.commit()
        await db.refresh(content)

        await emit_event(
            event_type=VisionEventType.CONTENT_CREATED,
            payload={
                "content_id": str(content.id),
                "content_type": content_type,
                "platform": platform,
            },
        )

        logger.info(f"Content created: {content.id}")
        return content

    async def update_status(
        self,
        db: AsyncSession,
        content_id: UUID,
        tenant_id: UUID,
        new_status: str,
    ) -> Optional[ContentItem]:
        """Atualiza o status de um conteúdo."""
        result = await db.execute(
            select(ContentItem).where(
                and_(
                    ContentItem.id == content_id,
                    ContentItem.tenant_id == tenant_id,
                )
            )
        )
        content = result.scalar_one_or_none()
        if not content:
            return None

        old_status = content.status
        content.status = new_status

        if new_status == "published":
            content.published_at = datetime.utcnow()

        await db.commit()

        await emit_event(
            event_type=VisionEventType.CONTENT_PUBLISHED if new_status == "published" else VisionEventType.CONTENT_CREATED,
            payload={
                "content_id": str(content_id),
                "old_status": old_status,
                "new_status": new_status,
            },
        )

        return content

    async def list_by_profile(
        self,
        db: AsyncSession,
        profile_id: UUID,
        tenant_id: UUID,
        status: Optional[str] = None,
    ) -> List[ContentItem]:
        """Lista conteúdos de um perfil."""
        query = select(ContentItem).where(
            and_(
                ContentItem.profile_id == profile_id,
                ContentItem.tenant_id == tenant_id,
            )
        )
        if status:
            query = query.where(ContentItem.status == status)

        result = await db.execute(query)
        return result.scalars().all()
