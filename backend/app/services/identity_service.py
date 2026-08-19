"""
IdentityService - Gerencia separacao Identity / Appearance / Character.

Regras:
- Identity: caracteristicas permanentes (face_shape, eye_color, height)
- Appearance: caracteristicas modificaveis (hair, beard, makeup)
- Character: tudo que e simulado para um personagem
"""

from typing import Dict, List, Any, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc

from app.models import IdentityTrait, AppearanceState, CharacterTransformation
from app.utils.logger import get_logger

logger = get_logger(__name__)


class IdentityService:
    """Servico para gerenciar identidade, aparencia e personagens."""

    async def register_identity_trait(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        profile_id: UUID,
        trait_category: str,
        trait_name: str,
        trait_value: str,
        confidence: float = 1.0,
        verified_by: Optional[str] = None,
    ) -> IdentityTrait:
        """Registra uma caracteristica identitaria permanente."""
        trait = IdentityTrait(
            tenant_id=tenant_id,
            profile_id=profile_id,
            trait_category=trait_category,
            trait_name=trait_name,
            trait_value=trait_value,
            confidence=confidence,
            verified_by=verified_by,
            is_permanent="true",
        )
        db.add(trait)
        await db.commit()
        await db.refresh(trait)
        logger.info(f"IdentityTrait registered: {trait_name}={trait_value} for profile {profile_id}")
        return trait

    async def get_identity_traits(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        profile_id: UUID,
    ) -> List[IdentityTrait]:
        """Retorna todas as caracteristicas identitarias de um perfil."""
        result = await db.execute(
            select(IdentityTrait).where(
                and_(
                    IdentityTrait.tenant_id == tenant_id,
                    IdentityTrait.profile_id == profile_id,
                    IdentityTrait.status == "active",
                )
            )
        )
        return result.scalars().all()

    async def get_identity_summary(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        profile_id: UUID,
    ) -> Dict[str, Any]:
        """Retorna resumo estruturado da identidade."""
        traits = await self.get_identity_traits(db, tenant_id, profile_id)
        summary = {}
        for trait in traits:
            if trait.trait_category not in summary:
                summary[trait.trait_category] = {}
            summary[trait.trait_category][trait.trait_name] = {
                "value": trait.trait_value,
                "confidence": float(trait.confidence) if trait.confidence else 1.0,
                "verified": trait.verified_by is not None,
                "verified_by": trait.verified_by,
            }
        return summary

    async def update_appearance(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        profile_id: UUID,
        category: str,
        attribute: str,
        new_value: str,
        changed_reason: str = "user_update",
    ) -> AppearanceState:
        """Atualiza o estado atual da aparencia."""
        # Busca estado anterior
        result = await db.execute(
            select(AppearanceState).where(
                and_(
                    AppearanceState.tenant_id == tenant_id,
                    AppearanceState.profile_id == profile_id,
                    AppearanceState.category == category,
                    AppearanceState.attribute == attribute,
                    AppearanceState.status == "active",
                )
            ).order_by(desc(AppearanceState.created_at))
        )
        previous = result.scalars().first()

        state = AppearanceState(
            tenant_id=tenant_id,
            profile_id=profile_id,
            category=category,
            attribute=attribute,
            current_value=new_value,
            previous_value=previous.current_value if previous else None,
            changed_at=__import__("datetime").datetime.utcnow(),
            changed_reason=changed_reason,
        )
        db.add(state)
        await db.commit()
        await db.refresh(state)
        logger.info(f"AppearanceState updated: {category}.{attribute}={new_value} for profile {profile_id}")
        return state

    async def get_current_appearance(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        profile_id: UUID,
    ) -> Dict[str, Any]:
        """Retorna estado atual da aparencia agrupado por categoria."""
        result = await db.execute(
            select(AppearanceState).where(
                and_(
                    AppearanceState.tenant_id == tenant_id,
                    AppearanceState.profile_id == profile_id,
                    AppearanceState.status == "active",
                )
            ).order_by(desc(AppearanceState.created_at))
        )
        states = result.scalars().all()

        appearance = {}
        seen = set()
        for state in states:
            key = (state.category, state.attribute)
            if key not in seen:
                seen.add(key)
                if state.category not in appearance:
                    appearance[state.category] = {}
                appearance[state.category][state.attribute] = {
                    "current_value": state.current_value,
                    "previous_value": state.previous_value,
                    "changed_at": state.changed_at.isoformat() if state.changed_at else None,
                    "changed_reason": state.changed_reason,
                }
        return appearance

    async def register_character_transformation(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        profile_id: UUID,
        character_id: UUID,
        transformation_type: str,
        attribute: str,
        value: str,
        simulation_prompt_fragment: Optional[str] = None,
    ) -> CharacterTransformation:
        """Registra uma transformacao de personagem (SEMPRE simulada)."""
        transform = CharacterTransformation(
            tenant_id=tenant_id,
            profile_id=profile_id,
            character_id=character_id,
            transformation_type=transformation_type,
            attribute=attribute,
            value=value,
            is_simulated="true",
            simulation_prompt_fragment=simulation_prompt_fragment,
        )
        db.add(transform)
        await db.commit()
        await db.refresh(transform)
        logger.info(f"CharacterTransformation registered: {transformation_type}.{attribute}={value} (SIMULATED)")
        return transform

    async def get_complete_profile_context(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        profile_id: UUID,
    ) -> Dict[str, Any]:
        """Retorna contexto completo: Identity + Appearance + Character."""
        identity = await self.get_identity_summary(db, tenant_id, profile_id)
        appearance = await self.get_current_appearance(db, tenant_id, profile_id)

        result = await db.execute(
            select(CharacterTransformation).where(
                and_(
                    CharacterTransformation.tenant_id == tenant_id,
                    CharacterTransformation.profile_id == profile_id,
                    CharacterTransformation.status == "active",
                )
            )
        )
        transforms = result.scalars().all()

        character_transformations = []
        for t in transforms:
            character_transformations.append({
                "character_id": str(t.character_id),
                "transformation_type": t.transformation_type,
                "attribute": t.attribute,
                "value": t.value,
                "is_simulated": t.is_simulated == "true",
                "simulation_prompt_fragment": t.simulation_prompt_fragment,
            })

        return {
            "identity": identity,
            "appearance": appearance,
            "character_transformations": {
                "count": len(character_transformations),
                "transformations": character_transformations,
            },
            "separation_warning": "NUNCA confundir character_transformations com identity ou appearance",
        }
