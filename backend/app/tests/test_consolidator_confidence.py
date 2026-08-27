"""
Testes do ResultConsolidator, com foco na normalização de "confidence".

Causa raiz do bug em produção: grooming/analyzer.py, photogenic/analyzer.py
e expressions/analyzer.py têm _calculate_confidence() retornando uma
categoria string ("high"/"medium"/"low") por design no caminho de SUCESSO
(não só em fallback de erro), enquanto colorimetry/analyzer.py já retorna
float corretamente. O consolidator somava esses valores direto com sum(),
quebrando com TypeError quando um módulo com confidence string chegava
"completed" (sem chave "error").
"""
import math

import pytest

from app.ai.consolidator.consolidator import ResultConsolidator


@pytest.fixture
def consolidator():
    return ResultConsolidator()


# ---------------------------------------------------------------------------
# _normalize_confidence - casos individuais pedidos na tarefa
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "raw_value,expected",
    [
        (0.85, 0.85),
        (1, 1.0),
        ("0.85", 0.85),
        ("85%", 0.85),
        (None, None),
        ("high", None),
        (True, None),
        (False, None),
        (float("nan"), None),
        (float("inf"), None),
        (float("-inf"), None),
    ],
)
def test_normalize_confidence_individual_cases(raw_value, expected):
    result = ResultConsolidator._normalize_confidence(raw_value)
    if expected is None:
        assert result is None
    else:
        assert result == pytest.approx(expected)


def test_normalize_confidence_rejects_bool_even_though_subclass_of_int():
    # bool é subclasse de int em Python (isinstance(True, int) == True),
    # mas True/False nunca devem ser tratados como confidence numérico.
    assert ResultConsolidator._normalize_confidence(True) is None
    assert ResultConsolidator._normalize_confidence(False) is None


def test_normalize_confidence_invalid_string_returns_none_not_zero():
    # Regra explícita: nunca transformar texto arbitrário em 0.0, pois
    # isso distorceria a média para baixo artificialmente.
    assert ResultConsolidator._normalize_confidence("not-a-number") is None
    assert ResultConsolidator._normalize_confidence("") is None
    assert ResultConsolidator._normalize_confidence("   ") is None


def test_normalize_confidence_clamps_out_of_range_numeric():
    assert ResultConsolidator._normalize_confidence(1.5) == 1.0
    assert ResultConsolidator._normalize_confidence(-0.3) == 0.0
    assert ResultConsolidator._normalize_confidence(150) == 1.0


def test_normalize_confidence_percentage_edge_cases():
    assert ResultConsolidator._normalize_confidence("100%") == 1.0
    assert ResultConsolidator._normalize_confidence("0%") == 0.0
    assert ResultConsolidator._normalize_confidence("120%") == 1.0  # clamped
    assert ResultConsolidator._normalize_confidence("  42.5%  ") == pytest.approx(0.425)


def test_normalize_confidence_unsupported_types_return_none():
    assert ResultConsolidator._normalize_confidence([0.5]) is None
    assert ResultConsolidator._normalize_confidence({"value": 0.5}) is None
    assert ResultConsolidator._normalize_confidence(object()) is None


# ---------------------------------------------------------------------------
# consolidate() - reprodução exata do bug de produção
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_consolidate_does_not_raise_when_module_confidence_is_string(consolidator):
    """Reproduz o TypeError original: um módulo 'completed' (sem chave
    'error') com confidence string não pode derrubar a consolidação."""
    results = {
        "facial_structure": {"symmetry_score": 0.9, "confidence": 0.9},
        "grooming": {"overall_score": 0.7, "confidence": "high"},  # bug real
    }

    # Antes da correção, isto levantava:
    # TypeError: unsupported operand type(s) for +: 'int' and 'str'
    consolidated = await consolidator.consolidate(photos=[{}], results=results, tenant_id="tenant-1")

    assert consolidated["status"] == "completed"
    assert consolidated["modules"]["grooming"]["status"] == "completed"
    # Só facial_structure (0.9) entrou na média -- "high" foi ignorado.
    assert consolidated["confidence_score"] == 0.9


@pytest.mark.asyncio
async def test_consolidate_mixed_valid_and_invalid_confidences(consolidator):
    """0.8, '0.6', '90%', 'invalid', None -- a média deve considerar
    somente os válidos: 0.8, 0.6, 0.9 -> média 0.7666... -> round(.,2) 0.77."""
    results = {
        "mod_a": {"confidence": 0.8},
        "mod_b": {"confidence": "0.6"},
        "mod_c": {"confidence": "90%"},
        "mod_d": {"confidence": "invalid"},
        "mod_e": {"confidence": None},
    }

    consolidated = await consolidator.consolidate(photos=[{}], results=results, tenant_id="tenant-1")

    assert consolidated["confidence_score"] == round((0.8 + 0.6 + 0.9) / 3, 2)


@pytest.mark.asyncio
async def test_consolidate_falls_back_to_default_when_no_valid_confidence(consolidator):
    results = {
        "mod_a": {"confidence": "high"},
        "mod_b": {"confidence": float("nan")},
        "mod_c": {"confidence": True},
    }

    consolidated = await consolidator.consolidate(photos=[{}], results=results, tenant_id="tenant-1")

    assert consolidated["confidence_score"] == 0.5


@pytest.mark.asyncio
async def test_consolidate_modules_with_error_key_excluded_from_confidence(consolidator):
    """Preserva o comportamento atual: módulo com 'error' vira status
    'failed' e nunca entra na média de confidence, mesmo se por acaso
    também tivesse uma chave 'confidence'."""
    results = {
        "mod_ok": {"confidence": 0.7},
        "mod_failed": {"error": "timeout", "confidence": 0.99},
    }

    consolidated = await consolidator.consolidate(photos=[{}], results=results, tenant_id="tenant-1")

    assert consolidated["modules"]["mod_failed"]["status"] == "failed"
    assert consolidated["modules"]["mod_failed"]["error"] == "timeout"
    assert consolidated["confidence_score"] == 0.7


@pytest.mark.asyncio
async def test_consolidate_preserves_photos_analyzed_and_structure(consolidator):
    photos = [{"id": "p1"}, {"id": "p2"}]
    results = {"facial_structure": {"confidence": 0.8, "symmetry_score": 0.85}}

    consolidated = await consolidator.consolidate(photos=photos, results=results, tenant_id="tenant-1")

    assert consolidated["photos_analyzed"] == 2
    assert "overall_assessment" in consolidated
    assert "development_plan" in consolidated
    assert consolidated["overall_assessment"]["strengths"] == ["Excelente simetria facial"]


@pytest.mark.asyncio
async def test_consolidate_no_confidence_key_at_all_uses_default(consolidator):
    results = {"mod_a": {"overall_score": 0.9}}  # sem "confidence"

    consolidated = await consolidator.consolidate(photos=[{}], results=results, tenant_id="tenant-1")

    assert consolidated["confidence_score"] == 0.5


@pytest.mark.asyncio
async def test_consolidate_development_plan_unaffected_by_confidence_type(consolidator):
    """Garante que o bug de confidence não quebra (nem muda) o restante
    do pipeline de consolidação (development_plan, visagism, casting)."""
    results = {
        "visagism": {"confidence": "medium", "recommended_hairstyles": ["undercut"]},
        "casting": {"confidence": 0.6, "character_types": ["leading_man"]},
    }

    consolidated = await consolidator.consolidate(photos=[{}], results=results, tenant_id="tenant-1")

    assert "Agendar sessao com cabeleireiro: undercut" in consolidated["development_plan"]["immediate_actions"]
    assert "Preparar self-tape para personagem tipo: leading_man" in consolidated["development_plan"]["immediate_actions"]
    assert consolidated["confidence_score"] == 0.6
