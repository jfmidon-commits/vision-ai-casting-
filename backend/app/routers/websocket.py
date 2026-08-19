from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import Dict, List
import json
import asyncio

from app.core.websocket import manager
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/ws", tags=["websocket"])

@router.websocket("/progress/{analysis_id}")
async def analysis_progress_ws(websocket: WebSocket, analysis_id: str):
    channel = f"analysis:{analysis_id}"
    await manager.connect(websocket, channel)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            # Echo back or process
            await manager.broadcast(message, channel)
    except WebSocketDisconnect:
        manager.disconnect(websocket, channel)

@router.websocket("/tenant/{tenant_id}")
async def tenant_ws(websocket: WebSocket, tenant_id: str):
    channel = f"tenant:{tenant_id}"
    await manager.connect(websocket, channel)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            await manager.broadcast(message, channel)
    except WebSocketDisconnect:
        manager.disconnect(websocket, channel)

class AnalysisProgressNotifier:
    @staticmethod
    async def notify_progress(analysis_id: str, tenant_id: str, progress: Dict):
        message = {
            "type": "analysis_progress",
            "analysis_id": analysis_id,
            "progress": progress,
            "timestamp": asyncio.get_event_loop().time(),
        }
        await manager.broadcast(message, f"analysis:{analysis_id}")
        await manager.broadcast(message, f"tenant:{tenant_id}")
    
    @staticmethod
    async def notify_complete(analysis_id: str, tenant_id: str, result: Dict):
        message = {
            "type": "analysis_complete",
            "analysis_id": analysis_id,
            "data": result,
            "timestamp": asyncio.get_event_loop().time(),
        }
        await manager.broadcast(message, f"analysis:{analysis_id}")
        await manager.broadcast(message, f"tenant:{tenant_id}")
    
    @staticmethod
    async def notify_error(analysis_id: str, tenant_id: str, error: str):
        message = {
            "type": "analysis_error",
            "analysis_id": analysis_id,
            "error": error,
            "timestamp": asyncio.get_event_loop().time(),
        }
        await manager.broadcast(message, f"analysis:{analysis_id}")
        await manager.broadcast(message, f"tenant:{tenant_id}")

progress_notifier = AnalysisProgressNotifier()
