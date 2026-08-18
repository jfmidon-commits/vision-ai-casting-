"""
IdentityPreservationService - Preservacao de Identidade.

Responsavel por:
- Armazenar referencias necessarias para preservar identidade em geracoes futuras
- Impedir que transformacao de personagem seja salva como caracteristica real
- Rastrear origem de todos os assets
- Garantir separacao: REAL vs CURRENT_APPEARANCE vs SIMULATED vs AI_GENERATED
"""

from typing import Dict, List, Any, Optional
from uuid import UUID
from datetime import datetime
from enum import Enum
import inspect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models import IdentityReference, AssetOriginLog, DigitalTwinAsset
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AssetOrigin(str, Enum):
    REAL = "REAL"
    CURRENT_APPEARANCE = "CURRENT_APPEARANCE"
    SIMULATED = "SIMULATED"
    AI_GENERATED = "AI_GENERATED"


class IdentityPreservationService:
    ORIGIN_DESCRIPTIONS = {
        AssetOrigin.REAL: "Foto real tirada por fotografo profissional",
        AssetOrigin.CURRENT_APPEARANCE: "Foto atual do talento - estado real atual",
        AssetOrigin.SIMULATED: "Simulacao de personagem - NAO E REAL",
        AssetOrigin.AI_GENERATED: "Imagem gerada por IA - NAO E REAL",
    }

    async def _execute(self, db: AsyncSession, statement):
        result = db.execute(statement)
        return await result if inspect.isawaitable(result) else result

    async def register_reference(self, db: AsyncSession, tenant_id: UUID, profile_id: UUID, file_url: str, reference_type: str, origin: AssetOrigin, asset_id: Optional[UUID] = None, quality_score: Optional[float] = None, metadata: Optional[Dict[str, Any]] = None, is_primary: bool = False) -> IdentityReference:
        reference = IdentityReference(tenant_id=tenant_id, profile_id=profile_id, asset_id=asset_id, reference_type=reference_type, origin=origin.value, file_url=file_url, quality_score=quality_score, metadata={**(metadata or {}), "origin_description": self.ORIGIN_DESCRIPTIONS[origin], "registered_at": datetime.utcnow().isoformat()}, is_primary="true" if is_primary else "false")
        db.add(reference)
        await db.commit(); await db.refresh(reference)
        await self._log_asset_origin(db, tenant_id, profile_id, asset_id, "photo", origin, self.ORIGIN_DESCRIPTIONS[origin])
        return reference

    async def get_identity_references(self, db: AsyncSession, profile_id: UUID, tenant_id: UUID, origin: Optional[AssetOrigin] = None, reference_type: Optional[str] = None) -> List[IdentityReference]:
        query = select(IdentityReference).where(and_(IdentityReference.profile_id == profile_id, IdentityReference.tenant_id == tenant_id, IdentityReference.status == "active"))
        if origin: query = query.where(IdentityReference.origin == origin.value)
        if reference_type: query = query.where(IdentityReference.reference_type == reference_type)
        result = await self._execute(db, query)
        return result.scalars().all()

    async def get_primary_references(self, db: AsyncSession, profile_id: UUID, tenant_id: UUID) -> Dict[str, IdentityReference]:
        result = await self._execute(db, select(IdentityReference).where(and_(IdentityReference.profile_id == profile_id, IdentityReference.tenant_id == tenant_id, IdentityReference.is_primary == "true", IdentityReference.status == "active")))
        references = result.scalars().all()
        return {r.reference_type: r for r in references}

    async def validate_asset_origin(self, db: AsyncSession, asset_id: UUID, tenant_id: UUID) -> Dict[str, Any]:
        result = await self._execute(db, select(AssetOriginLog).where(and_(AssetOriginLog.asset_id == asset_id, AssetOriginLog.tenant_id == tenant_id)))
        log = result.scalar_one_or_none()
        if not log:
            return {"asset_id": str(asset_id), "origin": "UNKNOWN", "warning": "Asset sem registro de origem - REQUER VERIFICACAO", "can_be_used_for_identity": False, "can_be_used_for_simulation": False}
        origin = log.origin
        can_use_for_identity = origin in [AssetOrigin.REAL.value, AssetOrigin.CURRENT_APPEARANCE.value]
        can_use_for_simulation = origin in [AssetOrigin.REAL.value, AssetOrigin.CURRENT_APPEARANCE.value, AssetOrigin.SIMULATED.value, AssetOrigin.AI_GENERATED.value]
        warnings = []
        if origin == AssetOrigin.AI_GENERATED.value: warnings.append("CRITICAL: Asset gerado por IA - NUNCA usar como referencia de identidade real")
        if origin == AssetOrigin.SIMULATED.value: warnings.append("WARNING: Asset simulado - usar apenas para referencia de personagem")
        if log.is_saved_as_real == "true" and origin != AssetOrigin.REAL.value: warnings.append("CRITICAL: Asset nao-real marcado como real - CORRIGIR IMEDIATAMENTE")
        return {"asset_id": str(asset_id), "origin": origin, "origin_description": self.ORIGIN_DESCRIPTIONS.get(AssetOrigin(origin), "Unknown"), "source_description": log.source_description, "generated_by": log.generated_by, "can_be_used_for_identity": can_use_for_identity, "can_be_used_for_simulation": can_use_for_simulation, "warnings": warnings, "is_safe": len([w for w in warnings if w.startswith("CRITICAL")]) == 0}

    async def prevent_confusion(self, db: AsyncSession, asset_id: UUID, tenant_id: UUID) -> Dict[str, Any]:
        validation = await self.validate_asset_origin(db, asset_id, tenant_id)
        actions = []
        if not validation.get("is_safe", False):
            result = await self._execute(db, select(AssetOriginLog).where(and_(AssetOriginLog.asset_id == asset_id, AssetOriginLog.tenant_id == tenant_id)))
            log = result.scalar_one_or_none()
            if log:
                current_flags = log.warning_flags or []
                if "IDENTITY_CONFUSION_RISK" not in current_flags:
                    current_flags.append("IDENTITY_CONFUSION_RISK"); log.warning_flags = current_flags; await db.commit()
                actions.append({"action": "flag_asset", "flag": "IDENTITY_CONFUSION_RISK", "reason": "Asset com risco de confusao de identidade"})
        if validation["origin"] in [AssetOrigin.SIMULATED.value, AssetOrigin.AI_GENERATED.value]:
            actions.append({"action": "block_save_as_real", "reason": "Assets simulados/IA nao podem ser salvos como caracteristicas reais"})
            result = await self._execute(db, select(DigitalTwinAsset).where(and_(DigitalTwinAsset.id == asset_id, DigitalTwinAsset.tenant_id == tenant_id)))
            asset = result.scalar_one_or_none()
            if asset and asset._metadata:
                metadata = dict(asset._metadata); metadata["identity_warning"] = "SIMULATED_ASSET - NOT REAL"; metadata["cannot_be_identity_reference"] = True; asset._metadata = metadata
                await db.commit(); actions.append({"action": "update_metadata", "reason": "Metadata atualizado com warning de identidade"})
        return {"asset_id": str(asset_id), "validation": validation, "actions_taken": actions, "is_protected": len(actions) > 0}

    async def get_identity_preservation_set(self, db: AsyncSession, profile_id: UUID, tenant_id: UUID) -> Dict[str, Any]:
        primary = await self.get_primary_references(db, profile_id, tenant_id)
        real_refs = await self.get_identity_references(db, profile_id, tenant_id, origin=AssetOrigin.REAL)
        current_refs = await self.get_identity_references(db, profile_id, tenant_id, origin=AssetOrigin.CURRENT_APPEARANCE)
        return {"profile_id": str(profile_id), "description": "Conjunto de referencias para preservacao de identidade em geracoes futuras", "primary_references": {ref_type: {"file_url": ref.file_url, "reference_type": ref.reference_type, "quality_score": float(ref.quality_score) if ref.quality_score else None, "metadata": ref.metadata} for ref_type, ref in primary.items()}, "real_references": [{"id": str(r.id), "reference_type": r.reference_type, "file_url": r.file_url, "quality_score": float(r.quality_score) if r.quality_score else None} for r in real_refs], "current_appearance_references": [{"id": str(r.id), "reference_type": r.reference_type, "file_url": r.file_url} for r in current_refs], "usage_instructions": {"for_generation": "Use primary_references para manter identidade", "for_comparison": "Compare com real_references para validar", "forbidden": "NUNCA usar SIMULATED ou AI_GENERATED como referencia de identidade"}}

    async def _log_asset_origin(self, db: AsyncSession, tenant_id: UUID, profile_id: UUID, asset_id: Optional[UUID], asset_type: str, origin: AssetOrigin, source_description: str, generated_by: Optional[str] = None, generation_prompt: Optional[str] = None, parent_asset_id: Optional[UUID] = None) -> AssetOriginLog:
        log = AssetOriginLog(tenant_id=tenant_id, profile_id=profile_id, asset_id=asset_id, asset_type=asset_type, origin=origin.value, source_description=source_description, generated_by=generated_by, generation_prompt=generation_prompt, parent_asset_id=parent_asset_id, is_saved_as_real="false", warning_flags=[])
        db.add(log); await db.commit(); await db.refresh(log); return log
