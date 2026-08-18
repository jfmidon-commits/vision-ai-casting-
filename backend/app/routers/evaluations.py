from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from uuid import UUID
from typing import Optional

from app.database import get_db
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/api/v1/evaluations", tags=["evaluations"])


@router.get("", response_model=dict)
async def list_evaluations(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return {"data": []}
