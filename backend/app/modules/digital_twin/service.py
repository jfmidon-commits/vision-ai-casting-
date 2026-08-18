"""DigitalTwinService - Servico de gerenciamento do Gemeo Digital v0.2."""

from typing import Dict, List, Any, Optional
from uuid import UUID
from datetime import datetime
import inspect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc

from app.models import DigitalTwinAsset, DigitalTwinVersion
from app.core.event_bus import emit_event, VisionEventType
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DigitalTwinService:
    async def _execute(self, db: AsyncSession, statement):
        result = db.execute(statement)
        return await result if inspect.isawaitable(result) else result

    async def _scalars(self, result):
        scalars = result.scalars()
        return await scalars if inspect.isawaitable(scalars) else scalars

    async def _maybe_await(self, value):
        return await value if inspect.isawaitable(value) else value

    async def create_asset(self, db: AsyncSession, tenant_id: UUID, profile_id: UUID, media_type: str, file_url: str, angle: Optional[str] = None, pose: Optional[str] = None, expression: Optional[str] = None, tags: Optional[List[str]] = None, quality_score: Optional[float] = None, metadata: Optional[Dict[str, Any]] = None, version_id: Optional[UUID] = None, asset_origin: Optional[str] = None) -> DigitalTwinAsset:
        asset = DigitalTwinAsset(tenant_id=tenant_id, profile_id=profile_id, media_type=media_type, file_url=file_url, angle=angle, pose=pose, expression=expression, tags=tags or [], quality_score=quality_score, _metadata={**(metadata or {}), "asset_origin": asset_origin or "REAL", "capture_metadata": {"lighting": metadata.get("lighting") if metadata else None, "clothing": metadata.get("clothing") if metadata else None, "capture_date": metadata.get("capture_date") if metadata else datetime.utcnow().isoformat(), "quality_score": quality_score, "source": metadata.get("source") if metadata else "manual_upload", "tags": tags or []}, "future_fields": {"embeddings": None, "landmarks": None, "depth_data": None, "representation_3d": None}})
        db.add(asset); await db.commit(); await db.refresh(asset)
        await emit_event(event_type=VisionEventType.DIGITAL_TWIN_ASSET_ADDED, payload={"asset_id": str(asset.id), "profile_id": str(profile_id), "media_type": media_type, "asset_origin": asset_origin or "REAL"})
        return asset

    async def get_assets_by_profile(self, db: AsyncSession, profile_id: UUID, tenant_id: UUID) -> List[DigitalTwinAsset]:
        result = await self._execute(db, select(DigitalTwinAsset).where(and_(DigitalTwinAsset.profile_id == profile_id, DigitalTwinAsset.tenant_id == tenant_id, DigitalTwinAsset.status == "active")))
        scalars = await self._scalars(result)
        return await self._maybe_await(scalars.all())

    async def get_assets_by_angle(self, db: AsyncSession, profile_id: UUID, angle: str) -> List[DigitalTwinAsset]:
        result = await self._execute(db, select(DigitalTwinAsset).where(and_(DigitalTwinAsset.profile_id == profile_id, DigitalTwinAsset.angle == angle, DigitalTwinAsset.status == "active")))
        scalars = await self._scalars(result)
        return await self._maybe_await(scalars.all())

    async def create_version(self, db: AsyncSession, tenant_id: UUID, profile_id: UUID, version_name: str, description: Optional[str] = None, created_reason: Optional[str] = None, identity_traits_snapshot: Optional[Dict] = None, appearance_state_snapshot: Optional[Dict] = None) -> DigitalTwinVersion:
        result = await self._execute(db, select(DigitalTwinVersion).where(and_(DigitalTwinVersion.profile_id == profile_id, DigitalTwinVersion.tenant_id == tenant_id)).order_by(desc(DigitalTwinVersion.version_number)))
        scalars = await self._scalars(result)
        last_version = await self._maybe_await(scalars.first())
        next_version_number = (last_version.version_number + 1) if last_version else 1
        if last_version and last_version.status == "active": last_version.status = "archived"; await db.commit()
        version = DigitalTwinVersion(tenant_id=tenant_id, profile_id=profile_id, version_number=next_version_number, version_name=version_name, description=description, created_reason=created_reason or "user_request", status="active", identity_traits_snapshot=identity_traits_snapshot or {}, appearance_state_snapshot=appearance_state_snapshot or {})
        db.add(version); await db.commit(); await db.refresh(version)
        assets = await self.get_assets_by_profile(db, profile_id, tenant_id)
        version.assets_summary = {"total_assets": len(assets), "by_media_type": {}, "by_angle": {}, "by_origin": {}}
        for asset in assets:
            mt = asset.media_type; version.assets_summary["by_media_type"][mt] = version.assets_summary["by_media_type"].get(mt, 0) + 1
            if asset.angle: version.assets_summary["by_angle"][asset.angle] = version.assets_summary["by_angle"].get(asset.angle, 0) + 1
            origin = asset._metadata.get("asset_origin", "UNKNOWN") if asset._metadata else "UNKNOWN"; version.assets_summary["by_origin"][origin] = version.assets_summary["by_origin"].get(origin, 0) + 1
        await db.commit()
        await emit_event(event_type=VisionEventType.DIGITAL_TWIN_UPDATED, payload={"version_id": str(version.id), "profile_id": str(profile_id), "version_number": next_version_number, "reason": created_reason})
        return version

    async def get_versions_by_profile(self, db: AsyncSession, profile_id: UUID, tenant_id: UUID) -> List[DigitalTwinVersion]:
        result = await self._execute(db, select(DigitalTwinVersion).where(and_(DigitalTwinVersion.profile_id == profile_id, DigitalTwinVersion.tenant_id == tenant_id)).order_by(desc(DigitalTwinVersion.version_number)))
        scalars = await self._scalars(result)
        return await self._maybe_await(scalars.all())

    async def get_active_version(self, db: AsyncSession, profile_id: UUID, tenant_id: UUID) -> Optional[DigitalTwinVersion]:
        result = await self._execute(db, select(DigitalTwinVersion).where(and_(DigitalTwinVersion.profile_id == profile_id, DigitalTwinVersion.tenant_id == tenant_id, DigitalTwinVersion.status == "active")))
        return await self._maybe_await(result.scalar_one_or_none())

    async def archive_version(self, db: AsyncSession, version_id: UUID, tenant_id: UUID) -> DigitalTwinVersion:
        result = await self._execute(db, select(DigitalTwinVersion).where(and_(DigitalTwinVersion.id == version_id, DigitalTwinVersion.tenant_id == tenant_id)))
        version = await self._maybe_await(result.scalar_one_or_none())
        if version: version.status = "archived"; await db.commit(); await db.refresh(version)
        return version

    async def compare_versions(self, db: AsyncSession, version_id_1: UUID, version_id_2: UUID, tenant_id: UUID) -> Dict[str, Any]:
        result1 = await self._execute(db, select(DigitalTwinVersion).where(and_(DigitalTwinVersion.id == version_id_1, DigitalTwinVersion.tenant_id == tenant_id)))
        result2 = await self._execute(db, select(DigitalTwinVersion).where(and_(DigitalTwinVersion.id == version_id_2, DigitalTwinVersion.tenant_id == tenant_id)))
        v1 = await self._maybe_await(result1.scalar_one_or_none())
        v2 = await self._maybe_await(result2.scalar_one_or_none())
        if not v1 or not v2: return {"error": "One or both versions not found"}
        return {"version_1": {"number": v1.version_number, "name": v1.version_name, "created_at": v1.created_at.isoformat()}, "version_2": {"number": v2.version_number, "name": v2.version_name, "created_at": v2.created_at.isoformat()}, "appearance_changes": self._compare_dicts(v1.appearance_state_snapshot or {}, v2.appearance_state_snapshot or {}), "identity_preserved": v1.identity_traits_snapshot == v2.identity_traits_snapshot, "assets_summary_comparison": {"v1": v1.assets_summary, "v2": v2.assets_summary}}

    def _compare_dicts(self, d1: Dict, d2: Dict) -> Dict[str, Any]:
        changes = {}
        for key in set(d1.keys()) | set(d2.keys()):
            v1, v2 = d1.get(key), d2.get(key)
            if v1 != v2: changes[key] = {"from": v1, "to": v2}
        return changes
