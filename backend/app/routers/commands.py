"""
Commands Router - API REST do Vision Core.

Endpoint principal para processar comandos dos usuários.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models import User
from app.schemas import APIResponse

router = APIRouter(prefix="/api/v1/commands", tags=["commands"])

_vision_core = None


def _get_vision_core():
    """Initialize Vision Core and its agents only when command APIs are used."""
    global _vision_core
    if _vision_core is None:
        from app.agents import (
            AnalyticsAgent,
            ApprovalAgent,
            AutomationAgent,
            CastingAgent,
            DigitalTwinAgent,
            IdentityAgent,
            OpportunityAgent,
            PortfolioAgent,
            SocialAgent,
            VisagismAgent,
        )
        from app.vision_core import VisionCoreService

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
        _vision_core = vision_core
    return _vision_core


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
    """Process a text or voice command through Vision Core."""
    vision_core = _get_vision_core()
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
    """Return command history for the current user."""
    vision_core = _get_vision_core()
    history = vision_core.get_command_history(
        user_id=current_user.id,
        limit=limit,
    )
    return APIResponse(data=history)


@router.get("/health", response_model=APIResponse)
async def get_vision_core_health():
    """Return Vision Core health, initializing it only on demand."""
    vision_core = _get_vision_core()
    return APIResponse(data=vision_core.get_health())
