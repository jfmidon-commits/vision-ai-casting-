from enum import Enum
from typing import Dict, List, Any, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models import IdentityReference, AssetOriginLog
from app.utils.logger import get_logger

logger = get_logger(__name__)

class AssetOrigin(Enum):
    REAL = "REAL"
    CURRENT_APPEARANCE = "CURRENT_APPEARANCE"
    SIMULATED = "SIMULATED"
    AI_GENERATED = "AI_GENERATED"

class IdentityPreservationService:
    async def register_reference(self, db, tenant_id, profile_id, file_url, reference_type, origin, quality_score=None, is_primary=False):
        ref = IdentityReference(
            tenant_id=tenant_id, profile_id=profile_id,
            file_url=file_url, reference_type=reference_type,
            origin=origin.value if isinstance(origin, AssetOrigin) else origin,
            quality_score=quality_score, is_primary="true" if is_primary else "false"
        )
        db.add(ref)
        await db.commit()
        await db.refresh(ref)
        return ref
    
    async def get_identity_references(self, db, tenant_id, profile_id, origin=None):
        query = select(IdentityReference).where(
            and_(IdentityReference.tenant_id == tenant_id, IdentityReference.profile_id == profile_id)
        )
        if origin:
            origin_val = origin.value if isinstance(origin, AssetOrigin) else origin
            query = query.where(IdentityReference.origin == origin_val)
        result = await db.execute(query)
        return result.scalars().all()
    
    async def validate_asset_origin(self, db, asset_id, tenant_id):
        result = await db.execute(
            select(AssetOriginLog).where(
                and_(AssetOriginLog.asset_id == asset_id, AssetOriginLog.tenant_id == tenant_id)
            )
        )
        log = result.scalar_one_or_none()
        if not log:
            return {"origin": "UNKNOWN", "can_be_used_for_identity": False, "can_be_used_for_simulation": False, "is_safe": False, "warnings": ["No origin log found"]}
        
        is_real = log.origin == "REAL"
        return {
            "origin": log.origin,
            "can_be_used_for_identity": is_real and log.is_saved_as_real == "false",
            "can_be_used_for_simulation": True,
            "is_safe": is_real,
            "warnings": ["CRITICAL: AI_GENERATED asset - NEVER use for identity reference"] if log.origin == "AI_GENERATED" else []
        }
    
    async def prevent_confusion(self, db, asset_id, tenant_id):
        validation = await self.validate_asset_origin(db, asset_id, tenant_id)
        actions = []
        if validation["origin"] in ["SIMULATED", "AI_GENERATED"]:
            actions.append({"action": "block_save_as_real", "reason": "Asset is not real"})
        return {"is_protected": True, "actions_taken": actions, "validation": validation}
    
    async def get_primary_references(self, db, tenant_id, profile_id):
        result = await db.execute(
            select(IdentityReference).where(
                and_(
                    IdentityReference.tenant_id == tenant_id,
                    IdentityReference.profile_id == profile_id,
                    IdentityReference.is_primary == "true"
                )
            )
        )
        refs = result.scalars().all()
        return {r.reference_type: r for r in refs}
    
    async def get_identity_preservation_set(self, db, tenant_id, profile_id):
        primary = await self.get_primary_references(db, tenant_id, profile_id)
        real_refs = await self.get_identity_references(db, tenant_id, profile_id, AssetOrigin.REAL)
        current_refs = await self.get_identity_references(db, tenant_id, profile_id, AssetOrigin.CURRENT_APPEARANCE)
        return {
            "primary_references": {k: {"file_url": v.file_url, "quality_score": float(v.quality_score) if v.quality_score else None} for k, v in primary.items()},
            "real_references": [{"id": str(r.id), "type": r.reference_type, "url": r.file_url} for r in real_refs],
            "current_appearance_references": [{"id": str(r.id), "type": r.reference_type, "url": r.file_url} for r in current_refs],
            "usage_instructions": {
                "allowed_for_identity": "ONLY REAL and CURRENT_APPEARANCE",
                "forbidden": "NUNCA usar SIMULATED ou AI_GENERATED como referencia de identidade",
                "primary_must_be": "face_frontal, face_profile, body_full"
            }
        }
    
    async def _log_asset_origin(self, db, tenant_id, profile_id, asset_id, asset_type, origin, source_description, generated_by=None, generation_prompt=None):
        log = AssetOriginLog(
            tenant_id=tenant_id, profile_id=profile_id, asset_id=asset_id,
            asset_type=asset_type, origin=origin.value if isinstance(origin, AssetOrigin) else origin,
            source_description=source_description, generated_by=generated_by,
            generation_prompt=generation_prompt
        )
        db.add(log)
        await db.commit()
        await db.refresh(log)
        return log
