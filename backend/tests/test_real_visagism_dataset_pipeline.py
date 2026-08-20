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
    pipeline = RealVisagismPipeline()

    result = pipeline.run(
        str(real_visagism_dataset),
        cut_limit=5,
        card_output_path=str(card_path),
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
