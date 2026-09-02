"""Authorization, isolation, and resource-bound tests for photo uploads."""

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, UploadFile

from app.routers import uploads as uploads_module
from app.services.storage_service import StorageService


def _scalar_result(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _db(value):
    db = AsyncMock()
    db.execute.return_value = _scalar_result(value)
    db.add = MagicMock()
    return db


def _upload_file(content=b"\xff\xd8\xffimage", content_type="image/jpeg"):
    file = AsyncMock(spec=UploadFile)
    file.filename = "portrait.jpg"
    file.content_type = content_type
    file.read = AsyncMock(side_effect=[content, b""])
    return file


@pytest.mark.asyncio
async def test_upload_rejects_photoshoot_outside_authenticated_tenant():
    db = _db(None)
    user = SimpleNamespace(id=uuid.uuid4(), tenant_id=uuid.uuid4())

    with patch.object(StorageService, "upload", new=AsyncMock()) as upload:
        with pytest.raises(HTTPException) as exc:
            await uploads_module.upload_photo(
                uuid.uuid4(), _upload_file(), current_user=user, db=db
            )

    assert exc.value.status_code == 404
    upload.assert_not_awaited()
    sql = str(db.execute.await_args.args[0])
    assert "photoshoots.tenant_id" in sql
    assert "profiles.tenant_id" in sql


@pytest.mark.asyncio
async def test_upload_uses_authenticated_tenant_in_database_and_object_key():
    tenant_id = uuid.uuid4()
    photoshoot_id = uuid.uuid4()
    profile_id = uuid.uuid4()
    db = _db(SimpleNamespace(id=photoshoot_id, profile_id=profile_id))
    user = SimpleNamespace(id=uuid.uuid4(), tenant_id=tenant_id)
    url = (
        "https://bucket.s3.sa-east-1.amazonaws.com/"
        f"tenants/{tenant_id}/photos/photo.jpg"
    )

    with patch.object(
        StorageService, "upload", new=AsyncMock(return_value=(url, url))
    ) as upload:
        await uploads_module.upload_photo(
            photoshoot_id, _upload_file(), current_user=user, db=db
        )

    assert upload.await_args.args[2] == str(tenant_id)
    photo = db.add.call_args.args[0]
    assert photo.tenant_id == tenant_id
    assert photo.profile_id == profile_id
    assert photo.photoshoot_id == photoshoot_id


@pytest.mark.asyncio
async def test_storage_key_is_namespaced_by_authenticated_tenant(monkeypatch):
    tenant_id = uuid.uuid4()
    client = MagicMock()
    monkeypatch.setattr(StorageService, "get_client", lambda: client)
    file = _upload_file()

    url, _ = await StorageService.upload(file, "photo-a", str(tenant_id))

    assert f"/tenants/{tenant_id}/photos/photo-a.jpg" in url
    assert client.upload_fileobj.call_args.args[2] == (
        f"tenants/{tenant_id}/photos/photo-a.jpg"
    )


@pytest.mark.asyncio
async def test_storage_rejects_oversized_image_before_s3_upload(monkeypatch):
    client = MagicMock()
    monkeypatch.setattr(StorageService, "get_client", lambda: client)
    file = _upload_file(
        content=b"x" * (StorageService.MAX_UPLOAD_BYTES + 1),
    )

    with pytest.raises(ValueError, match="image_too_large"):
        await StorageService.upload(file, "photo-a", "tenant-a")

    client.upload_fileobj.assert_not_called()


@pytest.mark.asyncio
async def test_upload_rejects_non_image_content_type_before_database_write():
    tenant_id = uuid.uuid4()
    photoshoot_id = uuid.uuid4()
    db = _db(SimpleNamespace(id=photoshoot_id, profile_id=uuid.uuid4()))
    user = SimpleNamespace(id=uuid.uuid4(), tenant_id=tenant_id)

    with pytest.raises(HTTPException) as exc:
        await uploads_module.upload_photo(
            photoshoot_id,
            _upload_file(content_type="application/x-executable"),
            current_user=user,
            db=db,
        )

    assert exc.value.status_code == 415
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_database_failure_removes_uploaded_object():
    tenant_id = uuid.uuid4()
    photoshoot_id = uuid.uuid4()
    db = _db(SimpleNamespace(id=photoshoot_id, profile_id=uuid.uuid4()))
    db.commit.side_effect = RuntimeError("database unavailable")
    user = SimpleNamespace(id=uuid.uuid4(), tenant_id=tenant_id)
    key = f"tenants/{tenant_id}/photos/photo.jpg"
    url = f"https://bucket.s3.sa-east-1.amazonaws.com/{key}"

    with patch.object(
        StorageService, "upload", new=AsyncMock(return_value=(url, url))
    ), patch.object(
        StorageService, "delete_file", new=AsyncMock(return_value=True)
    ) as delete_file:
        with pytest.raises(RuntimeError, match="database unavailable"):
            await uploads_module.upload_photo(
                photoshoot_id, _upload_file(), current_user=user, db=db
            )

    db.rollback.assert_awaited_once()
    delete_file.assert_awaited_once_with(key)
