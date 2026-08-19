"""Benchmark ponta a ponta para o ImageTriageEngine atual.

Este teste acompanha a API assíncrona definida em app.ai.image_triage:
ImageTriageEngine.triage(TriageInput) -> TriageResult.
"""

import json
import os
from pathlib import Path

import pytest

from app.ai.image_triage.engine import ImageTriageEngine
from app.ai.image_triage.schemas import FaceAngle, TriageInput, TriageResult


@pytest.fixture
def engine():
    return ImageTriageEngine()


@pytest.fixture
def dataset_path():
    paths = [
        os.path.join(os.path.dirname(__file__), "fixtures", "visagism", "dataset_001"),
        os.path.join(os.path.dirname(__file__), "..", "..", "tests", "fixtures", "visagism", "dataset_001"),
    ]
    for path in paths:
        if os.path.isdir(path):
            return path
    return paths[0]


@pytest.fixture
def benchmark_output_dir():
    output_dir = os.path.join(os.path.dirname(__file__), "..", "benchmark_output")
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


def require_dataset(dataset_path: str) -> None:
    if not os.path.isdir(dataset_path):
        pytest.skip("Dataset de benchmark não disponível")
    supported = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
    if not any(Path(dataset_path).rglob("*")):
        pytest.skip("Dataset de benchmark vazio")
    if not any(p.is_file() and p.suffix.lower() in supported for p in Path(dataset_path).rglob("*")):
        pytest.skip("Dataset de benchmark não contém imagens suportadas")


async def run_triage(engine: ImageTriageEngine, dataset_path: str) -> TriageResult:
    require_dataset(dataset_path)
    return await engine.triage(TriageInput(source_dir=dataset_path))


class TestSchemaContract:
    def test_protocol_categories_exist(self):
        expected = {
            "frontal",
            "three_quarter_left",
            "three_quarter_right",
            "profile_left",
            "profile_right",
            "smiling",
            "hairline",
            "posterior",
            "half_body",
        }
        assert expected.issubset({angle.value for angle in FaceAngle})

    def test_triage_result_type_is_current_schema(self):
        assert TriageResult.__name__ == "TriageResult"


class TestImageTriageBenchmark:
    @pytest.mark.asyncio
    async def test_triage_returns_valid_result(self, engine, dataset_path):
        result = await run_triage(engine, dataset_path)
        assert isinstance(result, TriageResult)
        assert result.total_images_found >= result.total_images_analyzed
        assert result.selected_count == len(result.selected)
        assert result.rejected_count == len(result.rejected)

    @pytest.mark.asyncio
    async def test_scores_between_zero_and_one(self, engine, dataset_path):
        result = await run_triage(engine, dataset_path)
        for candidate in result.selected + result.rejected:
            assert 0.0 <= candidate.face_confidence <= 1.0
            assert 0.0 <= candidate.overall_quality <= 1.0
            for score in candidate.quality_scores:
                assert 0.0 <= score.score <= 1.0
                assert 0.0 <= score.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_rejected_candidates_have_reason(self, engine, dataset_path):
        result = await run_triage(engine, dataset_path)
        for candidate in result.rejected:
            assert candidate.rejection_reasons, f"{candidate.filename}: rejeitada sem motivo"

    @pytest.mark.asyncio
    async def test_protocol_coverage_contract(self, engine, dataset_path):
        result = await run_triage(engine, dataset_path)
        coverage = result.get_protocol_coverage()
        expected = {
            FaceAngle.FRONTAL.value,
            FaceAngle.THREE_QUARTER_LEFT.value,
            FaceAngle.THREE_QUARTER_RIGHT.value,
            FaceAngle.PROFILE_LEFT.value,
            FaceAngle.PROFILE_RIGHT.value,
            FaceAngle.SMILING.value,
            FaceAngle.HAIRLINE.value,
            FaceAngle.POSTERIOR.value,
            FaceAngle.HALF_BODY.value,
        }
        assert set(coverage) == expected
        assert all(isinstance(value, bool) for value in coverage.values())
        assert 0.0 <= result.get_protocol_coverage_score() <= 1.0

    @pytest.mark.asyncio
    async def test_generate_benchmark_summary(self, engine, dataset_path, benchmark_output_dir):
        result = await run_triage(engine, dataset_path)
        coverage = result.get_protocol_coverage()
        summary = {
            "dataset_id": "Dataset_Referencia_001",
            "protocol_coverage": result.get_protocol_coverage_score(),
            "angles_detected": {name: int(present) for name, present in coverage.items()},
            "triage_selected_count": result.selected_count,
            "triage_rejected_count": result.rejected_count,
            "processing_time_seconds": result.processing_time_seconds,
        }
        output_path = os.path.join(benchmark_output_dir, "benchmark_summary.json")
        with open(output_path, "w", encoding="utf-8") as handle:
            json.dump(summary, handle, indent=2, ensure_ascii=False)
        assert os.path.exists(output_path)
