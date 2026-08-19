"""Benchmark real do dataset de referência do Visagism.

Valida três camadas independentes e complementares:
1. ImageTriageEngine e cobertura do protocolo de fotos.
2. MediaPipe FaceMesh + VisagismMeasurementEngine sobre foto real do dataset.
3. VisagismRuleEngine gerando recomendação principal + quatro alternativas.

Os artefatos gerados em backend/benchmark_output permitem auditar o resultado
sem depender apenas do status verde/vermelho do pytest.
"""

import json
import os
from pathlib import Path
from uuid import uuid4

import pytest
from PIL import Image

from app.ai.image_triage.engine import ImageTriageEngine
from app.ai.image_triage.schemas import FaceAngle, TriageInput, TriageResult
from app.ai.mediapipe.analyzer import MediaPipeService
from app.ai.visagism.evidence_tracker import EvidenceTracker
from app.ai.visagism.measurement_engine import VisagismMeasurementEngine
from app.ai.visagism.rule_engine import VisagismRuleEngine
from app.ai.visagism.schemas import FaceShape, PhotoAngle


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


@pytest.fixture
def frontal_image_path(dataset_path):
    require_dataset(dataset_path)
    preferred = Path(dataset_path) / "01_frontal_neutra_close.jpg"
    if preferred.exists():
        return preferred

    candidates = sorted(Path(dataset_path).glob("*frontal*.jpg"))
    if not candidates:
        pytest.skip("Dataset não contém foto frontal para validar FaceMesh")
    return candidates[0]


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


def as_json_value(value):
    """Converte enums/modelos simples em valor serializável para artefatos."""
    if hasattr(value, "value"):
        return value.value
    return value


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


class TestRealFaceMeshAndVisagism:
    @pytest.mark.asyncio
    async def test_facemesh_returns_complete_real_landmarks(
        self, frontal_image_path, benchmark_output_dir
    ):
        service = MediaPipeService()
        with Image.open(frontal_image_path) as source:
            image = source.convert("RGB")
            result = await service.analyze_face_mesh(image)

        assert not result.get("error"), result.get("error")
        assert result.get("landmarks_count", 0) >= 468
        assert len(result.get("landmarks", [])) >= 468
        assert "note" not in result, "FaceMesh não pode retornar biometria mock"
        assert 0.0 <= result.get("symmetry_score", 0.0) <= 1.0
        assert result.get("face_shape") not in {None, "unknown"}

        artifact = {
            "dataset_image": frontal_image_path.name,
            "landmarks_count": result["landmarks_count"],
            "symmetry_score": result.get("symmetry_score"),
            "facial_proportions": result.get("facial_proportions", {}),
            "face_shape": result.get("face_shape"),
            "eye_aspect_ratio": result.get("eye_aspect_ratio"),
            "mouth_aspect_ratio": result.get("mouth_aspect_ratio"),
            "mock_data": False,
        }
        output_path = Path(benchmark_output_dir) / "facemesh_result.json"
        output_path.write_text(
            json.dumps(artifact, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    @pytest.mark.asyncio
    async def test_measurements_and_five_haircut_recommendations(
        self, frontal_image_path, benchmark_output_dir
    ):
        measurement_engine = VisagismMeasurementEngine()
        tracker = EvidenceTracker()
        photo_id = uuid4()

        with Image.open(frontal_image_path) as source:
            image = source.convert("RGB")
            measured = await measurement_engine.measure_photo(
                photo_id=photo_id,
                image=image,
                angle=PhotoAngle.FRONT_NEUTRAL,
                tracker=tracker,
            )

        assert measured.get("success"), measured.get("error")
        assert measured.get("landmarks_count", 0) >= 468
        assert len(measured.get("measurements", [])) >= 10
        assert len(measured.get("proportions", [])) >= 6
        assert measured.get("face_shape") != FaceShape.UNKNOWN
        assert 0.0 <= measured.get("symmetry_score", 0.0) <= 1.0

        proportions = {
            p.name: {
                "value": p.value,
                "classification": getattr(p, "classification", "unknown"),
            }
            for p in measured.get("proportions", [])
        }

        recommendation_tracker = EvidenceTracker()
        primary, alternatives, discouraged = VisagismRuleEngine().generate_recommendations(
            face_shape=measured["face_shape"],
            proportions=proportions,
            regions=measured.get("regions", {}),
            hair={},
            asymmetries={},
            profile_context={},
            tracker=recommendation_tracker,
        )

        assert primary is not None
        assert primary.rank == 1
        assert len(alternatives) == 4
        assert [item.rank for item in alternatives] == [2, 3, 4, 5]
        assert discouraged

        recommendations = [primary] + alternatives
        assert len(recommendations) == 5
        assert len({item.name for item in recommendations}) == 5
        for item in recommendations:
            assert item.justification
            assert 0.0 <= item.confidence <= 1.0

        artifact = {
            "dataset_image": frontal_image_path.name,
            "face_shape": as_json_value(measured["face_shape"]),
            "symmetry_score": measured.get("symmetry_score"),
            "landmarks_count": measured.get("landmarks_count"),
            "measurements": {
                m.name: m.value for m in measured.get("measurements", [])
            },
            "proportions": {
                p.name: {
                    "value": p.value,
                    "classification": as_json_value(
                        getattr(p, "classification", "unknown")
                    ),
                }
                for p in measured.get("proportions", [])
            },
            "recommendations": [
                {
                    "rank": item.rank,
                    "name": item.name,
                    "justification": item.justification,
                    "confidence": item.confidence,
                    "volume_distribution": item.volume_distribution,
                    "forehead_exposure": as_json_value(
                        item.forehead_exposure_recommendation
                    ),
                    "side_treatment": as_json_value(item.side_treatment),
                }
                for item in recommendations
            ],
            "discouraged_cuts": [
                {
                    "name": item.name,
                    "reason": item.reason,
                    "alternative": item.alternative,
                    "confidence": item.confidence,
                }
                for item in discouraged
            ],
        }
        output_path = Path(benchmark_output_dir) / "visagism_result.json"
        output_path.write_text(
            json.dumps(artifact, indent=2, ensure_ascii=False), encoding="utf-8"
        )
