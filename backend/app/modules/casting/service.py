"""
CastingService - Serviço de gerenciamento de Castings.

Responsável por:
- Cadastrar oportunidades de casting
- Extrair requisitos estruturados
- Calcular compatibilidade com perfis
- Gerenciar candidaturas
"""

from typing import Dict, List, Any, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models import Casting, CastingMatch
from app.core.event_bus import emit_event, VisionEventType
from app.utils.logger import get_logger

logger = get_logger(__name__)


class CastingService:
    """Serviço de gerenciamento de Castings."""

    async def create_casting(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        title: str,
        description: Optional[str] = None,
        production: Optional[str] = None,
        role: Optional[str] = None,
        age_range: Optional[str] = None,
        gender_presentation: Optional[str] = None,
        physical_requirements: Optional[Dict] = None,
        skills_required: Optional[List[str]] = None,
        location: Optional[str] = None,
        payment: Optional[str] = None,
        deadline: Optional[Any] = None,
        source: Optional[str] = None,
        source_url: Optional[str] = None,
        requirements: Optional[Dict] = None,
    ) -> Casting:
        """Cria uma nova oportunidade de casting."""
        casting = Casting(
            tenant_id=tenant_id,
            title=title,
            description=description,
            production=production,
            role=role,
            age_range=age_range,
            gender_presentation=gender_presentation,
            physical_requirements=physical_requirements or {},
            skills_required=skills_required or [],
            location=location,
            payment=payment,
            deadline=deadline,
            source=source,
            source_url=source_url,
            requirements=requirements or {},
        )

        db.add(casting)
        await db.commit()
        await db.refresh(casting)

        await emit_event(
            event_type=VisionEventType.CASTING_CREATED,
            payload={
                "casting_id": str(casting.id),
                "title": title,
                "role": role,
            },
        )

        logger.info(f"Casting created: {casting.id}")
        return casting

    async def list_castings(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        status: Optional[str] = "open",
    ) -> List[Casting]:
        """Lista castings do tenant."""
        query = select(Casting).where(Casting.tenant_id == tenant_id)
        if status:
            query = query.where(Casting.status == status)

        result = await db.execute(query)
        return result.scalars().all()

    async def create_match(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        casting_id: UUID,
        profile_id: UUID,
        compatibility_score: float,
        matching_attributes: Optional[Dict] = None,
        missing_attributes: Optional[Dict] = None,
        recommendation: Optional[str] = None,
    ) -> CastingMatch:
        """Cria um match entre casting e perfil."""
        match = CastingMatch(
            tenant_id=tenant_id,
            casting_id=casting_id,
            profile_id=profile_id,
            compatibility_score=compatibility_score,
            matching_attributes=matching_attributes or {},
            missing_attributes=missing_attributes or {},
            recommendation=recommendation,
        )

        db.add(match)
        await db.commit()
        await db.refresh(match)

        await emit_event(
            event_type=VisionEventType.CASTING_MATCH_FOUND,
            payload={
                "match_id": str(match.id),
                "casting_id": str(casting_id),
                "profile_id": str(profile_id),
                "score": compatibility_score,
            },
        )

        return match
