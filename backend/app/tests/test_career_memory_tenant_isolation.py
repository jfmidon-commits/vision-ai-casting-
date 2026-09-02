"""
Testes de isolamento de tenant para o Career Memory router.

Cobrem a correcao do bug critico em que `get_tenant_id` dependia de
`request.state.tenant_id`, populado apenas por um `tenant_middleware`
que nunca era registrado em `main.py` -- toda chamada real a esses
endpoints retornava 400. O design original tambem confiava num header
`X-Tenant-ID` controlado pelo cliente, o que seria uma vulnerabilidade
de IDOR se o middleware fosse simplesmente registrado.

A correcao faz `get_tenant_id` derivar o tenant EXCLUSIVAMENTE de
`current_user.tenant_id` (resolvido a partir do JWT), seguindo o mesmo
padrao ja usado em `routers/analyses.py`.

Estes testes rodam contra a app FastAPI real (via TestClient), montando
apenas o `career_memory_router` e usando `dependency_overrides` para
simular usuarios autenticados sem precisar de um Postgres real. As
chamadas ao `CareerMemoryService` sao substituidas por fakes que apenas
capturam o `tenant_id` recebido -- o que valida o contrato do router
(JWT -> current_user -> tenant_id -> service), que e exatamente a
camada que foi corrigida.
"""

import importlib.util
import sys
import types
import uuid
from datetime import datetime
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Dependencias pesadas (mediapipe/cv2/sklearn/openai) sao usadas por outros
# routers importados via app.routers.__init__, mas nao pelo career_memory.
# Stub para permitir importar a app sem instalar todo o stack de visao
# computacional neste ambiente de teste.
_OPTIONAL_MODULES = {
    "openai": ("openai",),
    "mediapipe": ("mediapipe",),
    "cv2": ("cv2",),
    "sklearn": ("sklearn", "sklearn.cluster", "sklearn.metrics"),
}
for _root, _modules in _OPTIONAL_MODULES.items():
    if importlib.util.find_spec(_root) is None:
        for _name in _modules:
            sys.modules.setdefault(_name, types.ModuleType(_name))

from app.middleware.auth import get_current_user  # noqa: E402  # isort: skip
from app.routers import (  # noqa: E402  # isort: skip
    career_memory as career_memory_module,
)
from app.routers.career_memory import (  # noqa: E402  # isort: skip
    router as career_memory_router,
)


class FakeUser:
    """Substitui o model User real -- so precisamos de tenant_id/id/role."""

    def __init__(self, tenant_id, user_id=None, role="user"):
        self.id = user_id or uuid.uuid4()
        self.tenant_id = tenant_id
        self.role = role


def _make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(career_memory_router)
    return app


def _client_as(app: FastAPI, user: FakeUser) -> TestClient:
    """Client autenticado como `user` -- so o dependency de autenticacao e
    sobrescrito. get_tenant_id NAO e sobrescrito, entao a resolucao real
    do tenant (current_user.tenant_id) e exercitada em todo teste."""
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app)


@pytest.fixture
def tenant_a():
    return uuid.uuid4()


@pytest.fixture
def tenant_b():
    return uuid.uuid4()


def test_authenticated_user_gets_own_tenant_id(tenant_a):
    """Usuario autenticado -> tenant_id resolvido e sempre o do proprio usuario."""
    app = _make_app()
    client = _client_as(app, FakeUser(tenant_id=tenant_a))
    captured = {}

    async def fake_get_experiences(db, profile_id, tenant_id, limit):
        captured["tenant_id"] = tenant_id
        return []

    with patch.object(
        career_memory_module.career_service, "get_experiences", fake_get_experiences
    ):
        resp = client.get(f"/career/experiences/{uuid.uuid4()}")

    assert resp.status_code == 200
    assert captured["tenant_id"] == tenant_a


def test_header_cannot_override_jwt_tenant(tenant_a, tenant_b):
    """Um X-Tenant-ID no header tentando se passar por outro tenant e
    ignorado -- o tenant_id usado e sempre o do JWT."""
    app = _make_app()
    client = _client_as(app, FakeUser(tenant_id=tenant_a))
    captured = {}

    async def fake_get_experiences(db, profile_id, tenant_id, limit):
        captured["tenant_id"] = tenant_id
        return []

    with patch.object(
        career_memory_module.career_service, "get_experiences", fake_get_experiences
    ):
        resp = client.get(
            f"/career/experiences/{uuid.uuid4()}",
            headers={"X-Tenant-ID": str(tenant_b)},
        )

    assert resp.status_code == 200
    assert captured["tenant_id"] == tenant_a
    assert captured["tenant_id"] != tenant_b


def test_tenant_a_user_never_leaks_tenant_b_id_to_service(tenant_a, tenant_b):
    """Simula duas requisicoes de usuarios de tenants diferentes e confirma
    que cada uma propaga exclusivamente o proprio tenant_id ao service --
    a fronteira que antes podia ser contornada via header."""
    captured = []

    async def fake_get_talent_context(db, profile_id, tenant_id, include_private):
        captured.append(tenant_id)
        return {"profile_id": str(profile_id), "tenant_id": str(tenant_id)}

    with patch.object(
        career_memory_module.career_service, "getTalentContext", fake_get_talent_context
    ):
        app_a = _make_app()
        client_a = _client_as(app_a, FakeUser(tenant_id=tenant_a))
        resp_a = client_a.get(f"/career/context/{uuid.uuid4()}")

        app_b = _make_app()
        client_b = _client_as(app_b, FakeUser(tenant_id=tenant_b))
        resp_b = client_b.get(f"/career/context/{uuid.uuid4()}")

    assert resp_a.status_code == 200
    assert resp_b.status_code == 200
    assert captured == [tenant_a, tenant_b]
    assert captured[0] != captured[1]


def test_unauthenticated_request_rejected():
    """Sem Authorization header, a dependency real de autenticacao (nao
    sobrescrita) deve rejeitar a request antes de qualquer logica de
    negocio ser executada."""
    app = _make_app()
    client = TestClient(app)  # sem dependency_overrides
    resp = client.get(f"/career/experiences/{uuid.uuid4()}")
    assert resp.status_code in (401, 403)


def test_create_experience_persists_correct_tenant(tenant_a):
    """POST /career/experiences deve gravar com o tenant_id do usuario
    autenticado, nunca de um valor fornecido pelo cliente (o schema de
    entrada nem aceita tenant_id -- so o router/service decidem isso)."""
    app = _make_app()
    client = _client_as(app, FakeUser(tenant_id=tenant_a))
    captured = {}

    async def fake_create_experience(db, tenant_id, **kwargs):
        captured["tenant_id"] = tenant_id
        now = datetime.utcnow()
        return {
            "id": uuid.uuid4(),
            "tenant_id": tenant_id,
            "profile_id": kwargs["profile_id"],
            "title": kwargs["title"],
            "company": kwargs.get("company"),
            "project_name": kwargs.get("project_name"),
            "role": kwargs.get("role"),
            "character_name": kwargs.get("character_name"),
            "production_type": kwargs.get("production_type"),
            "director": kwargs.get("director"),
            "agency": kwargs.get("agency"),
            "start_date": kwargs.get("start_date"),
            "end_date": kwargs.get("end_date"),
            "location": kwargs.get("location"),
            "description": kwargs.get("description"),
            "skills_used": kwargs.get("skills_used") or [],
            "photos_used": kwargs.get("photos_used") or [],
            "video_url": kwargs.get("video_url"),
            "is_featured": "false",
            "status": "active",
            "metadata": kwargs.get("metadata") or {},
            "created_at": now,
            "updated_at": now,
        }

    payload = {
        "profile_id": str(uuid.uuid4()),
        "title": "Campanha de verão",
    }

    with patch.object(
        career_memory_module.career_service, "create_experience", fake_create_experience
    ):
        resp = client.post("/career/experiences", json=payload)

    assert resp.status_code == 201, resp.text
    assert captured["tenant_id"] == tenant_a
    assert resp.json()["tenant_id"] == str(tenant_a)


def test_search_memory_uses_jwt_tenant_not_header(tenant_a, tenant_b):
    """search_memory (rota de consulta agregada) tambem deve resolver o
    tenant exclusivamente pelo JWT, ignorando qualquer header."""
    app = _make_app()
    client = _client_as(app, FakeUser(tenant_id=tenant_a))
    captured = {}

    async def fake_search_memory(db, profile_id, tenant_id, query, entity_types, limit):
        captured["tenant_id"] = tenant_id
        return {"results": []}

    with patch.object(
        career_memory_module.career_service, "searchMemory", fake_search_memory
    ):
        resp = client.get(
            f"/career/search/{uuid.uuid4()}",
            params={"q": "campanha"},
            headers={"X-Tenant-ID": str(tenant_b)},
        )

    assert resp.status_code == 200
    assert captured["tenant_id"] == tenant_a
