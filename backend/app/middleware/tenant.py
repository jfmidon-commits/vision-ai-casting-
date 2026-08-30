from fastapi import Depends
from uuid import UUID

from app.middleware.auth import get_current_user
from app.models import User


async def get_tenant_id(current_user: User = Depends(get_current_user)) -> UUID:
    """
    Dependency que resolve o tenant_id do request.

    O tenant_id e derivado EXCLUSIVAMENTE do usuario autenticado via JWT
    (current_user.tenant_id) -- nunca de um header ou de qualquer outro
    dado fornecido pelo cliente. Um header como "X-Tenant-ID" jamais deve
    ser usado para autorizacao de tenant: um usuario autenticado poderia
    simplesmente trocar o header e acessar dados de outro tenant (IDOR).

    get_current_user ja exige um Bearer token valido (HTTPBearer e
    obrigatorio por padrao), entao esta dependency tambem garante
    autenticacao obrigatoria em qualquer endpoint que a utilize.
    """
    return current_user.tenant_id
