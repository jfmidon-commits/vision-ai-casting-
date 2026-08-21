from pathlib import Path

from app.ai.image_triage.engine import TriageCategory, TriageResult
from app.pipelines.visagism import RealVisagismPipeline


class FakeTriageEngine:
    def process_dataset(self, dataset_path):
        return [
            TriageResult(
                filename="front.jpg",
                category=TriageCategory.FRONTAL,
                confidence=0.95,
                selected=True,
            )
        ]

    def select_best_by_category(self, results):
        return {TriageCategory.FRONTAL: results[0]}


class FakeMeasurementEngine:
    def analyze_image(self, image_path):
        return {
            "face_detected": True,
            "face_shape": {
                "value": "oval",
                "confidence": 0.8,
                "status": "estimated",
            },
            "measurements": {},
            "limitations": [],
        }


class FakeGroomingAnalyzer:
    def analyze(self, image_bytes):
        return {
            "confidence": 0.9,
            "landmarks_detected": True,
            "dimensions": {
                "hair": {
                    "coverage_score": 0.7,
                    "volume_score": 0.6,
                    "texture_score": 0.5,
                    "shine_score": 0.4,
                    "neatness_score": 0.7,
                }
            },
        }


def test_integrated_pipeline_produces_five_recommendations(tmp_path: Path):
    (tmp_path / "front.jpg").write_bytes(b"test-image")
    pipeline = RealVisagismPipeline(
        triage_engine=FakeTriageEngine(),
        measurement_engine=FakeMeasurementEngine(),
        grooming_analyzer=FakeGroomingAnalyzer(),
    )

    result = pipeline.run(str(tmp_path))

    assert result["evidence_image"].endswith("front.jpg")
    assert result["measurements"]["face_shape"]["value"] == "oval"
    assert result["hair_analysis"]["estimated"]["visual_density"]["status"] == (
        "estimated"
    )
    assert len(result["cut_recommendations"]["options"]) == 5
    assert result["cut_recommendations"]["primary"] is not None


def test_pipeline_reports_when_no_facial_view_exists(tmp_path: Path):
    class NoFaceTriage(FakeTriageEngine):
        def process_dataset(self, dataset_path):
            return []

        def select_best_by_category(self, results):
            return {}

    pipeline = RealVisagismPipeline(
        triage_engine=NoFaceTriage(),
        measurement_engine=FakeMeasurementEngine(),
        grooming_analyzer=FakeGroomingAnalyzer(),
    )

    result = pipeline.run(str(tmp_path))

    assert result["cut_recommendations"]["options"] == []
    assert "no_suitable_facial_evidence_image" in result["limitations"]
