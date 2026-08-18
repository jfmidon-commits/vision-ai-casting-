"""
IdentityService - Gerenciamento da separacao Identity / Appearance / Character.

Responsavel por:
- Manter IdentityTraits (caracteristicas permanentes)
- Gerenciar AppearanceState (caracteristicas modificaveis)
- Registrar CharacterTransformation (simulacoes)
- Garantir que o sistema saiba: QUEM E vs COMO ESTA vs COMO FOI TRANSFORMADO
"""

from typing import Dict, List, Any, Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models import IdentityTrait, AppearanceState, CharacterTransformation
from app.core.event_bus import emit_event, VisionEventType
from app.utils.logger import get_logger

logger = get_logger(__name__)


class IdentityService:
    """Servico de gerenciamento de Identidade, Aparência e Personagem."""

    async def register_identity_trait(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        profile_id: UUID,
        trait_category: str,
        trait_name: str,
        trait_value: str,
        confidence: float = 1.0,
        source: str = "analysis",
        verified_by: Optional[str] = None,
        is_permanent: bool = True,
    ) -> IdentityTrait:
        """Registra uma caracteristica identitaria permanente."""
        trait = IdentityTrait(
            tenant_id=tenant_id,
            profile_id=profile_id,
            trait_category=trait_category,
            trait_name=trait_name,
            trait_value=trait_value,
            confidence=confidence,
            source=source,
            verified_by=verified_by,
            verified_at=datetime.utcnow() if verified_by else None,
            is_permanent="true" if is_permanent else "false",
        )
        db.add(trait)
        await db.commit()
        await db.refresh(trait)
        logger.info(f"IdentityTrait registered: {trait_name}={trait_value} for profile {profile_id}")
        return trait

    async def get_identity_traits(
        self,
        db: AsyncSession,
        profile_id: UUID,
        tenant_id: UUID,
        category: Optional[str] = None,
    ) -> List[IdentityTrait]:
        """Retorna caracteristicas identitarias de um perfil."""
        query = select(IdentityTrait).where(
            and_(
                IdentityTrait.profile_id == profile_id,
                IdentityTrait.tenant_id == tenant_id,
                IdentityTrait.status == "active",
            )
        )
        if category:
            query = query.where(IdentityTrait.trait_category == category)
        result = await db.execute(query)
        return result.scalars().all()

    async def get_identity_summary(
        self,
        db: AsyncSession,
        profile_id: UUID,
        tenant_id: UUID,
    ) -> Dict[str, Any]:
        """Retorna resumo estruturado de IdentityTraits."""
        traits = await self.get_identity_traits(db, profile_id, tenant_id)
        summary = {
            "facial_structure": {},
            "eye_characteristics": {},
            "physical_identifiers": {},
            "proportions": {},
        }
        for trait in traits:
            cat = trait.trait_category
            if cat in summary:
                summary[cat][trait.trait_name] = {
                    "value": trait.trait_value,
                    "confidence": float(trait.confidence) if trait.confidence else 1.0,
                    "verified": trait.verified_by is not None,
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
        changed_reason: str,
        version_id: Optional[UUID] = None,
        photos: Optional[List[str]] = None,
    ) -> AppearanceState:
        """Atualiza o estado atual de aparencia do talento."""
        result = await db.execute(
            select(AppearanceState).where(
                and_(
                    AppearanceState.profile_id == profile_id,
                    AppearanceState.tenant_id == tenant_id,
                    AppearanceState.category == category,
                    AppearanceState.attribute == attribute,
                    AppearanceState.status == "active",
                )
            )
        )
        previous = result.scalar_one_or_none()

        if previous:
            previous.status = "archived"
            await db.commit()

        state = AppearanceState(
            tenant_id=tenant_id,
            profile_id=profile_id,
            version_id=version_id,
            category=category,
            attribute=attribute,
            current_value=new_value,
            previous_value=previous.current_value if previous else None,
            changed_at=datetime.utcnow(),
            changed_reason=changed_reason,
            photos=photos or [],
        )
        db.add(state)
        await db.commit()
        await db.refresh(state)

        await emit_event(
            event_type=VisionEventType.DIGITAL_TWIN_UPDATED,
            payload={
                "profile_id": str(profile_id),
                "change_type": "appearance",
                "category": category,
                "attribute": attribute,
                "new_value": new_value,
            },
        )

        logger.info(f"AppearanceState updated: {category}.{attribute}={new_value} for profile {profile_id}")
        return state

    async def get_current_appearance(
        self,
        db: AsyncSession,
        profile_id: UUID,
        tenant_id: UUID,
    ) -> Dict[str, Any]:
        """Retorna o estado atual completo de aparencia."""
        result = await db.execute(
            select(AppearanceState).where(
                and_(
                    AppearanceState.profile_id == profile_id,
                    AppearanceState.tenant_id == tenant_id,
                    AppearanceState.status == "active",
                )
            )
        )
        states = result.scalars().all()

        appearance = {
            "hair": {},
            "facial_hair": {},
            "body": {},
            "makeup": {},
            "grooming": {},
            "accessories": {},
        }
        for state in states:
            cat = state.category
            if cat in appearance:
                appearance[cat][state.attribute] = {
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
        generated_asset_id: Optional[UUID] = None,
        version_id: Optional[UUID] = None,
    ) -> CharacterTransformation:
        """Registra uma transformacao de personagem (NAO e real)."""
        transformation = CharacterTransformation(
            tenant_id=tenant_id,
            profile_id=profile_id,
            character_id=character_id,
            version_id=version_id,
            transformation_type=transformation_type,
            attribute=attribute,
            value=value,
            is_simulated="true",
            simulation_prompt_fragment=simulation_prompt_fragment,
            generated_asset_id=generated_asset_id,
        )
        db.add(transformation)
        await db.commit()
        await db.refresh(transformation)

        logger.info(f"CharacterTransformation registered: {transformation_type}.{attribute} for character {character_id}")
        return transformation

    async def get_character_transformations(
        self,
        db: AsyncSession,
        profile_id: UUID,
        tenant_id: UUID,
        character_id: Optional[UUID] = None,
    ) -> List[CharacterTransformation]:
        """Retorna transformacoes de personagem."""
        query = select(CharacterTransformation).where(
            and_(
                CharacterTransformation.profile_id == profile_id,
                CharacterTransformation.tenant_id == tenant_id,
                CharacterTransformation.status == "active",
            )
        )
        if character_id:
            query = query.where(CharacterTransformation.character_id == character_id)
        result = await db.execute(query)
        return result.scalars().all()

    async def get_complete_profile_context(
        self,
        db: AsyncSession,
        profile_id: UUID,
        tenant_id: UUID,
    ) -> Dict[str, Any]:
        """
        Retorna o contexto completo com separacao clara:
        QUEM E A PESSOA vs COMO ELA ESTA vs COMO ELA FOI TRANSFORMADA
        """
        identity = await self.get_identity_summary(db, profile_id, tenant_id)
        appearance = await self.get_current_appearance(db, profile_id, tenant_id)

        result = await db.execute(
            select(CharacterTransformation).where(
                and_(
                    CharacterTransformation.profile_id == profile_id,
                    CharacterTransformation.tenant_id == tenant_id,
                    CharacterTransformation.status == "active",
                )
            )
        )
        transformations = result.scalars().all()

        return {
            "identity": {
                "description": "Caracteristicas relativamente permanentes - QUEM E A PESSOA",
                "traits": identity,
            },
            "appearance": {
                "description": "Caracteristicas modificaveis - COMO ELA ESTA ATUALMENTE",
                "state": appearance,
            },
            "character_transformations": {
                "description": "Caracteristicas de simulacao - COMO ELA FOI TRANSFORMADA PARA UM PERSONAGEM",
                "transformations": [
                    {
                        "character_id": str(t.character_id),
                        "type": t.transformation_type,
                        "attribute": t.attribute,
                        "value": t.value,
                        "is_simulated": t.is_simulated == "true",
                        "simulated": True,
                    }
                    for t in transformations
                ],
                "count": len(transformations),
            },
            "separation_warning": "NUNCA confundir character_transformations com identity ou appearance",
        }
