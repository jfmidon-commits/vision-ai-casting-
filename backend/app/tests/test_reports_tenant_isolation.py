"""Tenant-isolation and creation-contract tests for the reports router."""

import importlib.util
import sys
import types
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

# app.routers.__init__ imports AI routers too; they are irrelevant to these tests.
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

from app.routers import reports as reports_module  # noqa: E402  # isort: skip
from app.schemas import ReportCreate  # noqa: E402  # isort: skip


def _scalar_result(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _mock_db():
    db = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    return db


@pytest.mark.asyncio
async def test_create_report_rejects_profile_outside_authenticated_tenant():
    tenant_a = uuid.uuid4()
    db = _mock_db()
    db.execute.return_value = _scalar_result(None)
    user = SimpleNamespace(id=uuid.uuid4(), tenant_id=tenant_a)
    payload = ReportCreate(
        profile_id=uuid.uuid4(),
        photoshoot_id=uuid.uuid4(),
        title="Relatorio",
    )

    with pytest.raises(HTTPException) as exc:
        await reports_module.create_report(payload, current_user=user, db=db)

    assert exc.value.status_code == 404
    assert exc.value.detail == "Profile not found"
    db.add.assert_not_called()

    statement = db.execute.await_args.args[0]
    sql = str(statement)
    assert "profiles.id" in sql
    assert "profiles.tenant_id" in sql


@pytest.mark.asyncio
async def test_create_report_rejects_photoshoot_outside_tenant_or_profile():
    tenant_a = uuid.uuid4()
    profile_id = uuid.uuid4()
    db = _mock_db()
    db.execute.side_effect = [
        _scalar_result(SimpleNamespace(id=profile_id, tenant_id=tenant_a)),
        _scalar_result(None),
    ]
    user = SimpleNamespace(id=uuid.uuid4(), tenant_id=tenant_a)
    payload = ReportCreate(
        profile_id=profile_id,
        photoshoot_id=uuid.uuid4(),
        title="Relatorio",
    )

    with pytest.raises(HTTPException) as exc:
        await reports_module.create_report(payload, current_user=user, db=db)

    assert exc.value.status_code == 404
    assert exc.value.detail == "Photoshoot not found"
    db.add.assert_not_called()

    statement = db.execute.await_args_list[1].args[0]
    sql = str(statement)
    assert "photoshoots.id" in sql
    assert "photoshoots.tenant_id" in sql
    assert "photoshoots.profile_id" in sql


@pytest.mark.asyncio
async def test_create_report_uses_authenticated_tenant_and_only_mapped_fields():
    tenant_a = uuid.uuid4()
    profile_id = uuid.uuid4()
    photoshoot_id = uuid.uuid4()
    user_id = uuid.uuid4()
    db = _mock_db()
    db.execute.side_effect = [
        _scalar_result(SimpleNamespace(id=profile_id, tenant_id=tenant_a)),
        _scalar_result(
            SimpleNamespace(
                id=photoshoot_id,
                tenant_id=tenant_a,
                profile_id=profile_id,
            )
        ),
    ]
    user = SimpleNamespace(id=user_id, tenant_id=tenant_a)
    payload = ReportCreate(
        profile_id=profile_id,
        photoshoot_id=photoshoot_id,
        title="Relatorio seguro",
        sections=["facial", "casting"],
        template="premium",
        language="pt-BR",
    )

    with patch.object(
        reports_module.ReportResponse, "model_validate", return_value={"ok": True}
    ):
        response = await reports_module.create_report(payload, current_user=user, db=db)

    created = db.add.call_args.args[0]
    assert created.tenant_id == tenant_a
    assert created.created_by == user_id
    assert created.profile_id == profile_id
    assert created.photoshoot_id == photoshoot_id
    assert created.title == "Relatorio seguro"
    assert "sections" not in created.__dict__
    assert "template" not in created.__dict__
    assert "language" not in created.__dict__
    assert response.message == "Report created"
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once_with(created)


@pytest.mark.asyncio
async def test_generate_pdf_revalidates_legacy_report_references():
    """Even a pre-existing Report row must not generate a PDF from another tenant's profile."""
    tenant_a = uuid.uuid4()
    report = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=tenant_a,
        profile_id=uuid.uuid4(),
        photoshoot_id=uuid.uuid4(),
    )
    db = _mock_db()
    db.execute.side_effect = [
        _scalar_result(report),
        _scalar_result(None),
    ]
    user = SimpleNamespace(id=uuid.uuid4(), tenant_id=tenant_a)

    with patch.object(
        reports_module.ReportService, "generate_pdf", new=AsyncMock()
    ) as generate_pdf:
        with pytest.raises(HTTPException) as exc:
            await reports_module.generate_pdf(report.id, current_user=user, db=db)

    assert exc.value.status_code == 404
    assert exc.value.detail == "Profile not found"
    generate_pdf.assert_not_awaited()
    db.commit.assert_not_awaited()
