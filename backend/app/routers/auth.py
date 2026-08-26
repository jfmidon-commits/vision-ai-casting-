from fastapi import APIRouter, Body, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional
from uuid import UUID
from app.database import get_db
from app.models import User, Tenant
from app.schemas import Token, LoginRequest, APIResponse, ErrorResponse
from app.services.auth_service import AuthService
from app.middleware.auth import get_current_user, require_role

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", response_model=APIResponse)
async def register(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await AuthService.register_user(db, request)
        return APIResponse(success=True, data=result, message="User registered successfully")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login", response_model=Token)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    try:
        return await AuthService.authenticate(db, request.email, request.password)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db)
):
    try:
        return await AuthService.refresh_token(db, refresh_token)
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.get("/me", response_model=APIResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    return APIResponse(success=True, data={
        "id": str(current_user.id),
        "email": current_user.email,
        "name": current_user.name,
        "role": current_user.role,
        "tenant_id": str(current_user.tenant_id),
    })


@router.post("/invites", response_model=APIResponse)
async def invite_user(
    email: str,
    role: str = "user",
    current_user: User = Depends(require_role(["admin", "manager"])),
    db: AsyncSession = Depends(get_db)
):
    try:
        invite = await AuthService.create_invite(db, current_user.tenant_id, email, role)
        return APIResponse(success=True, data=invite)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
