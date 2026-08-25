"""
Testes FASE 1: validação de formato seguro, suffix de tempfile, e logging de triage.
Nenhum assert True. Nenhum placeholder.
"""

import logging
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.routers.photos import _safe_suffix_from_format, _public_triage_contract, triage_photo
from app.routers.uploads import _normalize_image_format
from app.ai.image_triage.engine import TriageCategory, TriageResult


# ========== FIXTURES ==========

@pytest.fixture
def mock_user():
    user = MagicMock()
    user.id = uuid4()
    user.tenant_id = uuid4()
    user.clerk_id = "test_clerk_123"
    user.email = "test@example.com"
    user.name = "Test User"
    user.role = "user"
    return user


@pytest.fixture
def mock_photo(mock_user):
    photo = MagicMock()
    photo.id = uuid4()
    photo.tenant_id = mock_user.tenant_id
    photo.url = "https://vision-ai-casting-media.s3.us-east-2.amazonaws.com/photos/test.jpg"
    photo.format = "jpg"
    photo.angle = "front"
    photo.profile_id = uuid4()
    photo.photoshoot_id = uuid4()
    return photo


@pytest.fixture
def mock_db_session(mock_photo):
    """Cria um mock de AsyncSession que retorna a foto mockada."""
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_photo
    session.execute = AsyncMock(return_value=mock_result)
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session


# ========== TESTES: _safe_suffix_from_format (photos.py) ==========

class TestSafeSuffixFromFormat:
    def test_none_returns_jpg(self):
        assert _safe_suffix_from_format(None) == ".jpg"

    def test_empty_string_returns_jpg(self):
        assert _safe_suffix_from_format("") == ".jpg"

    def test_whitespace_returns_jpg(self):
        assert _safe_suffix_from_format("   ") == ".jpg"

    def test_jpg(self):
        assert _safe_suffix_from_format("jpg") == ".jpg"

    def test_jpeg_normalized_to_jpg(self):
        assert _safe_suffix_from_format("jpeg") == ".jpg"
        assert _safe_suffix_from_format("JPEG") == ".jpg"
        assert _safe_suffix_from_format(".jpeg") == ".jpg"

    def test_png(self):
        assert _safe_suffix_from_format("png") == ".png"
        assert _safe_suffix_from_format(".png") == ".png"

    def test_webp(self):
        assert _safe_suffix_from_format("webp") == ".webp"

    def test_heic(self):
        assert _safe_suffix_from_format("heic") == ".heic"

    def test_heif_normalized_to_heic(self):
        assert _safe_suffix_from_format("heif") == ".heic"
        assert _safe_suffix_from_format("HEIF") == ".heic"

    def test_raw(self):
        assert _safe_suffix_from_format("raw") == ".raw"

    def test_invalid_format_fallback_to_jpg(self):
        assert _safe_suffix_from_format("exe") == ".jpg"
        assert _safe_suffix_from_format("pdf") == ".jpg"
        assert _safe_suffix_from_format("txt") == ".jpg"

    def test_dot_only_returns_jpg(self):
        assert _safe_suffix_from_format(".") == ".jpg"

    def test_never_returns_dot_alone(self):
        for fmt in [None, "", ".", "   ", "exe"]:
            suffix = _safe_suffix_from_format(fmt)
            assert suffix != "."
            assert suffix != ""
            assert suffix.startswith(".")
            assert len(suffix) > 1


# ========== TESTES: _normalize_image_format (uploads.py) ==========

class TestNormalizeImageFormat:
    def test_none_none_returns_jpg(self):
        assert _normalize_image_format(None, None) == "jpg"

    def test_empty_filename_none_ct_returns_jpg(self):
        assert _normalize_image_format("", None) == "jpg"

    def test_jpg_from_filename(self):
        assert _normalize_image_format("photo.jpg", None) == "jpg"

    def test_jpeg_from_filename_normalized(self):
        assert _normalize_image_format("photo.jpeg", None) == "jpg"

    def test_png_from_filename(self):
        assert _normalize_image_format("photo.png", None) == "png"

    def test_webp_from_filename(self):
        assert _normalize_image_format("photo.webp", None) == "webp"

    def test_heic_from_filename(self):
        assert _normalize_image_format("photo.heic", None) == "heic"

    def test_heif_from_filename_normalized(self):
        assert _normalize_image_format("photo.heif", None) == "heic"

    def test_filename_without_extension_uses_content_type(self):
        assert _normalize_image_format("IMG_2024", "image/png") == "png"

    def test_filename_without_extension_uses_jpeg_ct(self):
        assert _normalize_image_format("IMG_2024", "image/jpeg") == "jpg"

    def test_content_type_with_charset(self):
        assert _normalize_image_format("IMG_2024", "image/jpeg; charset=utf-8") == "jpg"

    def test_invalid_extension_uses_content_type(self):
        assert _normalize_image_format("photo.exe", "image/png") == "png"

    def test_invalid_extension_invalid_ct_fallback_jpg(self):
        assert _normalize_image_format("photo.exe", "application/pdf") == "jpg"

    def test_filename_priority_over_content_type(self):
        assert _normalize_image_format("photo.png", "image/jpeg") == "png"

    def test_multiple_dots_in_filename(self):
        assert _normalize_image_format("my.photo.jpg", None) == "jpg"

    def test_raw_from_filename(self):
        assert _normalize_image_format("photo.raw", None) == "raw"

    def test_uppercase_extension_normalized(self):
        assert _normalize_image_format("photo.JPG", None) == "jpg"
        assert _normalize_image_format("photo.PNG", None) == "png"

    def test_no_extension_no_content_type(self):
        assert _normalize_image_format("photo", None) == "jpg"

    def test_whitespace_filename(self):
        assert _normalize_image_format("   ", None) == "jpg"


# ========== TESTES: contrato público preservado ==========

class TestPublicTriageContract:
    def test_accepts_frontal(self):
        photo_id = uuid4()
        result = TriageResult(
            filename="front.jpg",
            category=TriageCategory.FRONTAL,
            confidence=0.91,
            rejection_reasons=[],
            selected=True,
        )
        payload = _public_triage_contract(photo_id, result)
        assert payload["photo_id"] == str(photo_id)
        assert payload["accepted"] is True
        assert payload["category"] == "frontal"
        assert payload["selected"] is True
        assert payload["confidence"] == 0.91
        assert payload["rejection_reasons"] == []

    def test_rejects_unknown_even_when_selected(self):
        result = TriageResult(
            filename="unknown.jpg",
            category=TriageCategory.UNKNOWN,
            confidence=0.4,
            rejection_reasons=["angle_uncertain"],
            selected=True,
        )
        payload = _public_triage_contract(uuid4(), result)
        assert payload["accepted"] is False
        assert payload["category"] == "unknown"

    def test_rejects_explicit_rejected(self):
        result = TriageResult(
            filename="bad.jpg",
            category=TriageCategory.REJECTED,
            confidence=0.2,
            rejection_reasons=["no_face_detected"],
            selected=False,
        )
        payload = _public_triage_contract(uuid4(), result)
        assert payload["accepted"] is False
        assert payload["selected"] is False
        assert payload["category"] == "rejected"

    def test_fails_closed_without_result(self):
        payload = _public_triage_contract(uuid4(), reason="triage_error")
        assert payload["accepted"] is False
        assert payload["selected"] is False
        assert payload["category"] == "rejected"
        assert payload["confidence"] == 0.0
        assert payload["rejection_reasons"] == ["triage_error"]

    def test_does_not_expose_raw_scores(self):
        result = TriageResult(
            filename="front.jpg",
            category=TriageCategory.FRONTAL_CLOSE,
            confidence=0.88,
            scores={"yaw": 0.12, "face": 0.99},
            metadata={"landmarks": [1, 2, 3]},
            selected=True,
        )
        payload = _public_triage_contract(uuid4(), result)
        assert "scores" not in payload
        assert "metadata" not in payload
        assert "landmarks" not in payload


# ========== TESTES: tempfile real com suffix seguro ==========

class TestTempfileWithSafeSuffix:
    def test_mkstemp_with_jpg_suffix(self):
        suffix = _safe_suffix_from_format("jpg")
        fd, path = tempfile.mkstemp(suffix=suffix)
        try:
            assert path.endswith(".jpg")
            with os.fdopen(fd, "wb") as f:
                f.write(b"fake_image_data")
            assert os.path.getsize(path) == 15
        finally:
            os.unlink(path)

    def test_mkstemp_with_png_suffix(self):
        suffix = _safe_suffix_from_format("png")
        fd, path = tempfile.mkstemp(suffix=suffix)
        try:
            assert path.endswith(".png")
            os.close(fd)
        finally:
            os.unlink(path)

    def test_mkstemp_never_creates_dot_suffix(self):
        bad_formats = [None, "", ".", "   ", "exe", "pdf", "txt", "php"]
        for fmt in bad_formats:
            suffix = _safe_suffix_from_format(fmt)
            fd, path = tempfile.mkstemp(suffix=suffix)
            os.close(fd)
            os.unlink(path)
            assert suffix == ".jpg", f"Formato {fmt!r} deveria cair em .jpg, mas deu {suffix!r}"


# ========== TESTES: exception no triage é logada e retorna fail-closed ==========

class TestTriageExceptionLogging:
    """
    Testa triage_photo() diretamente com mocks explícitos (sem TestClient).
    Provoca falha em StorageService.read_object_from_url e verifica:
    1. logger.exception executado com [TRIAGE_EXCEPTION]
    2. Retorno é APIResponse com accepted=false, rejection_reasons=["triage_error"]
    """

    @pytest.mark.asyncio
    @patch("app.routers.photos.StorageService.read_object_from_url")
    async def test_s3_exception_logged_and_fail_closed(
        self, mock_read_s3, mock_photo, mock_user, mock_db_session, caplog
    ):
        # Configurar caplog para capturar ERROR do logger do módulo
        caplog.set_level(logging.ERROR, logger="app.routers.photos")

        # Provocar exceção no S3
        mock_read_s3.side_effect = RuntimeError("S3 connection timeout")

        # Executar a função diretamente, passando mocks como argumentos posicionais
        # (bypassando Depends do FastAPI)
        response = await triage_photo(
            photo_id=mock_photo.id,
            current_user=mock_user,
            db=mock_db_session,
        )

        # 1. Verificar que o log contém TRIAGE_EXCEPTION
        assert "[TRIAGE_EXCEPTION]" in caplog.text
        assert str(mock_photo.id) in caplog.text
        assert "RuntimeError" in caplog.text
        assert "S3 connection timeout" in caplog.text

        # 2. Verificar contrato público fail-closed (APIResponse model)
        assert response.success is True  # Wrapper APIResponse sempre success=True
        assert response.data["accepted"] is False
        assert response.data["category"] == "rejected"
        assert response.data["confidence"] == 0.0
        assert response.data["selected"] is False
        assert response.data["rejection_reasons"] == ["triage_error"]
        assert response.message == "Photo triage blocked safely"
