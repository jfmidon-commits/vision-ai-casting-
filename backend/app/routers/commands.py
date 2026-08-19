"""
Commands Router - API REST do Vision Core.

Endpoint principal para processar comandos dos usuários.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models import User
from app.schemas import APIResponse
from app.vision_core import VisionCoreService
from app.agents import (
    IdentityAgent, VisagismAgent, DigitalTwinAgent,
    CastingAgent, PortfolioAgent, SocialAgent,
    OpportunityAgent, ApprovalAgent, AnalyticsAgent,
    AutomationAgent,
)

router = APIRouter(prefix="/api/v1/commands", tags=["commands"])

# Inicializa o Vision Core com todos os agentes
vision_core = VisionCoreService()
vision_core.register_agents([
    IdentityAgent(),
    VisagismAgent(),
    DigitalTwinAgent(),
    CastingAgent(),
    PortfolioAgent(),
    SocialAgent(),
    OpportunityAgent(),
    ApprovalAgent(),
    AnalyticsAgent(),
    AutomationAgent(),
])


class CommandRequest(BaseModel):
    input_type: str = "text"  # text | voice
    text: str
    metadata: Optional[Dict[str, Any]] = {}


@router.post("", response_model=APIResponse)
async def process_command(
    request: CommandRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Endpoint principal do Vision Core.

    Recebe comandos de texto ou voz e os processa através
    do orquestrador central.
    """
    result = await vision_core.process_command(
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        input_type=request.input_type,
        text=request.text,
        metadata=request.metadata,
    )

    return APIResponse(
        success=result["success"],
        data=result,
        message="Command processed" if result["success"] else result.get("error"),
    )


@router.get("/history", response_model=APIResponse)
async def get_command_history(
    current_user: User = Depends(get_current_user),
    limit: int = 50,
):
    """Retorna histórico de comandos do usuário."""
    history = vision_core.get_command_history(
        user_id=current_user.id,
        limit=limit,
    )
    return APIResponse(data=history)


@router.get("/health", response_model=APIResponse)
async def get_vision_core_health():
    """Retorna saúde do Vision Core."""
    return APIResponse(data=vision_core.get_health())
