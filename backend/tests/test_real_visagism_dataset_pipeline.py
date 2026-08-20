import json
import os
from pathlib import Path

import pytest
from PIL import Image

from app.pipelines.visagism import RealVisagismPipeline


@pytest.fixture
def real_visagism_dataset():
    path = Path(__file__).parent / "fixtures" / "visagism" / "dataset_001"
    if not path.exists():
        pytest.skip("Real visagism benchmark dataset not available")
    return path


def test_real_dataset_runs_through_reproducible_pipeline(
    real_visagism_dataset: Path,
    tmp_path: Path,
):
    card_path = tmp_path / "barber_card.png"
    manifest_path = tmp_path / "artifacts.json"
    pipeline = RealVisagismPipeline()

    result = pipeline.run(
        str(real_visagism_dataset),
        cut_limit=5,
        card_output_path=str(card_path),
        include_report=True,
        artifact_manifest_path=str(manifest_path),
    )

    assert result["triage"]["processed_images"] >= 10
    assert result["evidence_image"]
    assert os.path.exists(result["evidence_image"])
    assert len(result["cut_recommendations"]["options"]) == 5
    assert result["cut_recommendations"]["primary"] is not None
    assert result["simulation"]["available"] is False
    assert result["simulation"]["provider"] == "none"

    assert card_path.exists()
    with Image.open(card_path) as card:
        assert card.size == (1080, 1920)
        assert card.format == "PNG"

    assert result["card"]["synthetic_simulation_used"] is False
    assert result["report"]["schema_version"] == "1.0"
    assert result["report"]["evidence"]["processed_images"] >= 10
    assert result["report"]["integrity"]["physical_measurements_claimed"] is False
    assert result["report"]["integrity"]["synthetic_simulation_presented_as_real"] is False

    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["artifacts"]["card"]["exists"] is True
    assert len(manifest["artifacts"]["card"]["sha256"]) == 64
