from app.ai.image_triage.engine import TriageCategory, TriageResult
from app.pipelines.visagism import RealVisagismPipeline


class FakeTriageEngine:
    def process_dataset(self, dataset_path):
        return [
            TriageResult(
                filename="front.jpg",
                category=TriageCategory.FRONTAL,
                confidence=0.92,
                scores={"yaw": 1.2},
                selected=True,
            ),
            TriageResult(
                filename="right.jpg",
                category=TriageCategory.PROFILE_RIGHT,
                confidence=0.88,
                scores={"yaw": 71.0},
                selected=True,
            ),
        ]

    def select_best_by_category(self, results):
        return {result.category: result for result in results if result.selected}


def test_run_triage_preserves_real_evidence_contract():
    pipeline = RealVisagismPipeline(triage_engine=FakeTriageEngine())

    output = pipeline.run_triage("/tmp/dataset")

    assert output["processed_images"] == 2
    assert output["evidence_source"] == "ImageTriageEngine"
    assert output["selected_views"]["frontal"]["filename"] == "front.jpg"
    assert output["selected_views"]["profile_right"]["scores"]["yaw"] == 71.0
    assert "three_quarter_left" in output["missing_views"]
    assert "missing_required_views" in output["limitations"]


def test_run_triage_reports_empty_dataset_without_inventing_data():
    class EmptyEngine(FakeTriageEngine):
        def process_dataset(self, dataset_path):
            return []

    pipeline = RealVisagismPipeline(triage_engine=EmptyEngine())

    output = pipeline.run_triage("/tmp/empty")

    assert output["processed_images"] == 0
    assert output["selected_views"] == {}
    assert "no_images_processed" in output["limitations"]
