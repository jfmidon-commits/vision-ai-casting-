"""
P0.1 corrective tests — contracts, mock ban, triage, no fake cuts.
"""
import io
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from PIL import Image

from app.ai.visagism.analyzer import VisagismAnalyzer
from app.services.ai_service import (
    _pil_to_jpeg_bytes,
    _first_image_bytes,
    _is_facial_mock,
)


def _make_pil():
    img = Image.new("RGB", (64, 64), color=(120, 80, 60))
    return img


def test_pil_to_jpeg_bytes_format():
    img = _make_pil()
    data = _pil_to_jpeg_bytes(img)
    assert isinstance(data, (bytes, bytearray))
    assert len(data) > 50
    # JPEG magic
    assert data[:2] == b"\xff\xd8"


def test_first_image_bytes_from_preprocessed():
    prep = [{"photo_id": "1", "image": _make_pil()}]
    data = _first_image_bytes(prep)
    assert data and data[:2] == b"\xff\xd8"


def test_first_image_bytes_empty():
    assert _first_image_bytes([]) is None
    assert _first_image_bytes([{"photo_id": "1"}]) is None


def test_is_facial_mock_true():
    mock = {
        "face_shape": "oval",
        "sources": {"mediapipe": "mock", "deepface": "mock", "rekognition": "mock"},
    }
    assert _is_facial_mock(mock) is True
    assert _is_facial_mock({"is_mock": True}) is True


def test_is_facial_mock_false_real():
    real = {
        "face_shape": "oval",
        "sources": {"mediapipe": "ok", "deepface": "ok"},
    }
    assert _is_facial_mock(real) is False


@pytest.fixture
def analyzer():
    with patch("app.ai.visagism.analyzer.openai.AsyncOpenAI") as mock_openai:
        inst = MagicMock()
        mock_openai.return_value = inst
        a = VisagismAnalyzer()
        a.client = inst
        yield a


@pytest.mark.asyncio
async def test_mock_facial_not_in_measured(analyzer):
    parallel = {
        "facial_structure": {
            "face_shape": "diamond",
            "sources": {"mediapipe": "mock", "deepface": "mock", "rekognition": "mock"},
        }
    }
    fake_llm = {
        "face_shape_category": "desconhecido",
        "recommended_hairstyles": ["A", "B", "C", "D", "E"],
        "primary_hairstyle": "A",
        "confidence": 0.5,
    }
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content=json.dumps(fake_llm)))]
    analyzer.client.chat.completions.create = AsyncMock(return_value=mock_resp)

    result = await analyzer.analyze_single(
        {"id": "1"}, context={"parallel_results": parallel}
    )
    assert result["measured_data_used"].get("face_shape") is None
    assert "facial_result_is_mock" in result.get("limitations", [])
    assert result["measured_data_used"].get("face_shape") != "diamond"


@pytest.mark.asyncio
async def test_no_fake_complementary_cuts(analyzer):
    fake_llm = {
        "recommended_hairstyles": ["A", "B"],
        "primary_hairstyle": "A",
        "confidence": 0.6,
    }
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content=json.dumps(fake_llm)))]
    analyzer.client.chat.completions.create = AsyncMock(return_value=mock_resp)

    result = await analyzer.analyze_single({"id": "1"}, context={})
    styles = result["recommended_hairstyles"]
    assert len(styles) == 2
    assert all("complementar" not in s.lower() for s in styles)
    assert any("fewer_than_5_grounded_hairstyles" in x for x in result.get("limitations", []))


@pytest.mark.asyncio
async def test_primary_must_belong_to_list(analyzer):
    fake_llm = {
        "recommended_hairstyles": ["Corte A", "Corte B", "Corte C"],
        "primary_hairstyle": "Corte Inventado",
        "confidence": 0.7,
    }
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content=json.dumps(fake_llm)))]
    analyzer.client.chat.completions.create = AsyncMock(return_value=mock_resp)

    result = await analyzer.analyze_single({"id": "1"}, context={})
    assert result["primary_hairstyle"] in result["recommended_hairstyles"]
    assert "primary_hairstyle_not_in_recommendations" in result.get("limitations", [])


@pytest.mark.asyncio
async def test_real_grooming_reaches_measured(analyzer):
    parallel = {
        "grooming": {
            "dimensions": {
                "hair": {
                    "coverage_score": 0.9,
                    "volume_score": 0.5,
                    "texture_score": 0.5,
                    "neatness_score": 0.5,
                    "overall_score": 0.6,
                }
            }
        }
    }
    fake_llm = {
        "recommended_hairstyles": ["X", "Y", "Z", "W", "V"],
        "primary_hairstyle": "X",
        "confidence": 0.8,
    }
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content=json.dumps(fake_llm)))]
    analyzer.client.chat.completions.create = AsyncMock(return_value=mock_resp)

    result = await analyzer.analyze_single(
        {"id": "1"}, context={"parallel_results": parallel}
    )
    assert result["measured_data_used"]["hair_density"] == "alta"
    assert result["current_hair"]["density"] == "alta"


@pytest.mark.asyncio
async def test_previous_p0_uses_parallel_still_works(analyzer):
    """Regression: original P0 test behavior."""
    parallel = {
        "grooming": {
            "dimensions": {
                "hair": {
                    "coverage_score": 0.82,
                    "volume_score": 0.7,
                    "texture_score": 0.6,
                    "neatness_score": 0.75,
                    "overall_score": 0.72,
                }
            }
        },
        "colorimetry": {
            "skin_undertone": "warm",
            "skin_depth": "medium",
            "season": "Autumn",
        },
        "photogenic": {
            "overall_score": 0.81,
            "dimensions": {"symmetry": {"score": 0.78}},
        },
        "facial_structure": {
            "face_shape": "oval",
            "sources": {"mediapipe": "ok"},
        },
    }
    fake_llm = {
        "face_shape_category": "oval",
        "recommended_hairstyles": ["A", "B", "C", "D", "E"],
        "primary_hairstyle": "A",
        "confidence": 0.85,
    }
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content=json.dumps(fake_llm)))]
    analyzer.client.chat.completions.create = AsyncMock(return_value=mock_resp)

    result = await analyzer.analyze_single(
        {"id": "1", "url": "http://x"}, context={"parallel_results": parallel}
    )
    assert result["measured_data_used"]["hair_density"] == "alta"
    assert result["measured_data_used"]["face_shape"] == "oval"
    assert result["measured_data_used"]["skin_undertone"] == "warm"
    assert len(result["recommended_hairstyles"]) == 5
    assert result["primary_hairstyle"] == "A"
