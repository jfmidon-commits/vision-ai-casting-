"""
Testes específicos P0 – VisagismAnalyzer consome parallel_results.
Não dependem de OpenAI real (mock do client).
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

from app.ai.visagism.analyzer import VisagismAnalyzer


@pytest.fixture
def analyzer():
    with patch("app.ai.visagism.analyzer.openai.AsyncOpenAI") as mock_openai:
        inst = MagicMock()
        mock_openai.return_value = inst
        a = VisagismAnalyzer()
        a.client = inst
        yield a


@pytest.mark.asyncio
async def test_uses_parallel_results(analyzer):
    """Confirma que parallel_results são extraídos e aparecem em measured_data_used."""
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
        "facial_structure": {"face_shape": "oval"},
    }

    fake_llm = {
        "face_shape_category": "oval",
        "face_shape_description": "Oval medido",
        "recommended_hairstyles": ["A", "B", "C", "D", "E"],
        "primary_hairstyle": "A",
        "primary_justification": "Baseado em coverage alta e formato oval",
        "current_hair": {"summary": "Volume médio-alto", "density": "alta", "hairline": "detectado"},
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
    assert result["measured_data_used"]["symmetry"] == 0.78
    assert len(result["recommended_hairstyles"]) == 5
    assert result["primary_hairstyle"] == "A"
    assert "grooming_analyzer_not_available" not in result.get("limitations", [])


@pytest.mark.asyncio
async def test_missing_engines_produce_limitations(analyzer):
    """Quando motores não estão presentes, limitations devem ser explícitas."""
    fake_llm = {
        "face_shape_category": "desconhecido",
        "recommended_hairstyles": ["1", "2", "3", "4", "5"],
        "primary_hairstyle": "1",
        "primary_justification": "Dados limitados",
        "confidence": 0.4,
    }
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content=json.dumps(fake_llm)))]
    analyzer.client.chat.completions.create = AsyncMock(return_value=mock_resp)

    result = await analyzer.analyze_single(
        {"id": "1"}, context={"parallel_results": {}}
    )

    lims = result.get("limitations", [])
    assert "grooming_analyzer_not_available" in lims
    assert "colorimetry_analyzer_not_available" in lims
    assert result["current_hair"]["density"] == "não medido"
    assert len(result["recommended_hairstyles"]) == 5


@pytest.mark.asyncio
async def test_does_not_pad_fake_cuts(analyzer):
    """P0.1-E: não completa com cortes inventados."""
    fake_llm = {
        "recommended_hairstyles": ["A", "B"],  # LLM devolveu só 2
        "primary_hairstyle": "A",
        "confidence": 0.6,
    }
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content=json.dumps(fake_llm)))]
    analyzer.client.chat.completions.create = AsyncMock(return_value=mock_resp)

    result = await analyzer.analyze_single({"id": "1"}, context={})
    assert len(result["recommended_hairstyles"]) == 2
    assert all("complementar" not in s.lower() for s in result["recommended_hairstyles"])


@pytest.mark.asyncio
async def test_no_photos(analyzer):
    result = await analyzer.analyze([])
    assert "error" in result
