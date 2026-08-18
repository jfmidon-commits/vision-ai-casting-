"""
ApprovalService - Serviço de Workflow de Aprovação.

Responsável por:
- Criar solicitações de aprovação
- Gerenciar estados (pending, approved, rejected, revision_requested)
- Integrar com conectores de mensagem (WhatsApp mock)
- Emitir eventos de aprovação
"""

from typing import Dict, List, Any, Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models import ContentApproval
from app.core.event_bus import emit_event, VisionEventType
from app.connectors import MockWhatsAppConnector
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ApprovalService:
    """Serviço de Workflow de Aprovação."""

    def __init__(self):
        self.whatsapp = MockWhatsAppConnector()

    async def create_approval(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        content_item_id: UUID,
        approval_type: str,  # CONTENT, CASTING_APPLICATION, PROFILE_CHANGE, EXTERNAL_ACTION
        requested_by: UUID,
        recipient_phone: Optional[str] = None,
        content_preview: Optional[str] = None,
        media_url: Optional[str] = None,
    ) -> ContentApproval:
        """Cria uma nova solicitação de aprovação."""
        approval = ContentApproval(
            tenant_id=tenant_id,
            content_item_id=content_item_id,
            approval_type=approval_type,
            requested_by=requested_by,
            status="pending",
        )

        db.add(approval)
        await db.commit()
        await db.refresh(approval)

        # Envia notificação mock via WhatsApp
        if recipient_phone:
            await self.whatsapp.send_approval_request(
                recipient=recipient_phone,
                content_preview=content_preview or "Novo conteúdo para aprovação",
                media_url=media_url,
                approval_id=str(approval.id),
            )

        await emit_event(
            event_type=VisionEventType.CONTENT_APPROVAL_REQUESTED,
            payload={
                "approval_id": str(approval.id),
                "content_item_id": str(content_item_id),
                "approval_type": approval_type,
            },
        )

        logger.info(f"Approval created: {approval.id}")
        return approval

    async def get_approval(
        self,
        db: AsyncSession,
        approval_id: UUID,
        tenant_id: UUID,
    ) -> Optional[ContentApproval]:
        """Busca uma aprovação por ID."""
        result = await db.execute(
            select(ContentApproval).where(
                and_(
                    ContentApproval.id == approval_id,
                    ContentApproval.tenant_id == tenant_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def list_pending(
        self,
        db: AsyncSession,
        tenant_id: UUID,
    ) -> List[ContentApproval]:
        """Lista aprovações pendentes."""
        result = await db.execute(
            select(ContentApproval).where(
                and_(
                    ContentApproval.tenant_id == tenant_id,
                    ContentApproval.status == "pending",
                )
            )
        )
        return result.scalars().all()
