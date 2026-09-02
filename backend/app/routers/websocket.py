import asyncio
from typing import Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.websocket import manager
from app.database import get_db
from app.models import Analysis, User

router = APIRouter(prefix="/ws", tags=["websocket"])


def _extract_websocket_token(websocket: WebSocket) -> Optional[str]:
    authorization = websocket.headers.get("authorization", "")
    scheme, _, credentials = authorization.partition(" ")
    if scheme.lower() == "bearer" and credentials:
        return credentials

    protocols = [
        value.strip()
        for value in websocket.headers.get("sec-websocket-protocol", "").split(",")
    ]
    if len(protocols) >= 2 and protocols[0].lower() == "bearer":
        return protocols[1]
    return None


async def _authenticate_websocket(
    websocket: WebSocket, db: AsyncSession
) -> Optional[User]:
    token = _extract_websocket_token(websocket)
    if not token:
        await websocket.close(code=4401, reason="Authentication required")
        return None

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        user_id = payload.get("sub")
        if not user_id:
            raise JWTError("missing subject")
    except JWTError:
        await websocket.close(code=4401, reason="Invalid credentials")
        return None

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        await websocket.close(code=4401, reason="Invalid credentials")
        return None
    return user


def _analysis_channel(tenant_id: object, analysis_id: object) -> str:
    return f"tenant:{tenant_id}:analysis:{analysis_id}"


async def _receive_server_only(websocket: WebSocket, connection_id: str) -> None:
    while True:
        data = await websocket.receive_json()
        event_type = data.get("event_type") or data.get("type")
        if event_type == "ping":
            await manager.handle_ping(connection_id)
        else:
            await manager.send_to_connection(
                connection_id,
                {
                    "event_type": "error",
                    "payload": {"message": "Client publishing is not allowed"},
                },
            )


@router.websocket("/progress/{analysis_id}")
async def analysis_progress_ws(
    websocket: WebSocket,
    analysis_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    user = await _authenticate_websocket(websocket, db)
    if user is None:
        return

    result = await db.execute(
        select(Analysis).where(
            and_(
                Analysis.id == analysis_id,
                Analysis.tenant_id == user.tenant_id,
            )
        )
    )
    if result.scalar_one_or_none() is None:
        await websocket.close(code=4404, reason="Resource not found")
        return

    channel = _analysis_channel(user.tenant_id, analysis_id)
    connection_id = await manager.connect(
        websocket,
        channel,
        metadata={"user_id": str(user.id), "tenant_id": str(user.tenant_id)},
    )
    try:
        await _receive_server_only(websocket, connection_id)
    except WebSocketDisconnect:
        manager.disconnect(connection_id)


@router.websocket("/tenant")
@router.websocket("/tenant/{tenant_id}")
async def tenant_ws(
    websocket: WebSocket,
    tenant_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Subscribe to the authenticated tenant; a legacy path value is ignored."""
    user = await _authenticate_websocket(websocket, db)
    if user is None:
        return

    channel = f"tenant:{user.tenant_id}"
    connection_id = await manager.connect(
        websocket,
        channel,
        metadata={"user_id": str(user.id), "tenant_id": str(user.tenant_id)},
    )
    try:
        await _receive_server_only(websocket, connection_id)
    except WebSocketDisconnect:
        manager.disconnect(connection_id)


class AnalysisProgressNotifier:
    @staticmethod
    async def notify_progress(analysis_id: str, tenant_id: str, progress: Dict):
        message = {
            "type": "analysis_progress",
            "analysis_id": analysis_id,
            "progress": progress,
            "timestamp": asyncio.get_event_loop().time(),
        }
        await manager.broadcast(message, _analysis_channel(tenant_id, analysis_id))
        await manager.broadcast(message, f"tenant:{tenant_id}")

    @staticmethod
    async def notify_complete(analysis_id: str, tenant_id: str, result: Dict):
        message = {
            "type": "analysis_complete",
            "analysis_id": analysis_id,
            "data": result,
            "timestamp": asyncio.get_event_loop().time(),
        }
        await manager.broadcast(message, _analysis_channel(tenant_id, analysis_id))
        await manager.broadcast(message, f"tenant:{tenant_id}")

    @staticmethod
    async def notify_error(analysis_id: str, tenant_id: str, error: str):
        message = {
            "type": "analysis_error",
            "analysis_id": analysis_id,
            "error": error,
            "timestamp": asyncio.get_event_loop().time(),
        }
        await manager.broadcast(message, _analysis_channel(tenant_id, analysis_id))
        await manager.broadcast(message, f"tenant:{tenant_id}")


progress_notifier = AnalysisProgressNotifier()
