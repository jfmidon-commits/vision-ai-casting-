from fastapi import Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from app.database import get_db
from app.models import Tenant

async def tenant_middleware(request: Request, call_next):
    tenant_id = request.headers.get("X-Tenant-ID")
    if tenant_id:
        request.state.tenant_id = tenant_id
    response = await call_next(request)
    return response


async def get_tenant_id(request: Request) -> UUID:
    """
    Dependency para extrair tenant_id do request state.
    Usado pelos routers que precisam do tenant_id explicitamente.
    """
    tenant_id = request.state.tenant_id if hasattr(request.state, "tenant_id") else None
    if not tenant_id:
        raise HTTPException(status_code=400, detail="X-Tenant-ID header required")
    try:
        return UUID(tenant_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid X-Tenant-ID format")
