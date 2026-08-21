import json
import os
from pathlib import Path

from PIL import Image

from app.pipelines.visagism import RealVisagismPipeline


def test_current_dataset_runs_full_visagism_pipeline():
    dataset = Path(
        os.getenv(
            "CURRENT_VISAGISM_DATASET",
            "../assets/reference_photos/juliano_midon/visagismo_2026-08-21",
        )
    ).resolve()
    output_dir = Path("benchmark_output").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    assert dataset.exists(), f"Dataset não encontrado: {dataset}"
    images = [
        p
        for p in dataset.iterdir()
        if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
    ]
    assert len(images) >= 3, f"Poucas imagens no dataset atual: {len(images)}"

    card_path = output_dir / "barber_card.png"
    manifest_path = output_dir / "artifacts.json"
    result_path = output_dir / "current_visagism_result.json"

    pipeline = RealVisagismPipeline()
    result = pipeline.run(
        str(dataset),
        cut_limit=5,
        card_output_path=str(card_path),
        include_report=True,
        artifact_manifest_path=str(manifest_path),
    )

    assert result["triage"]["processed_images"] >= 3
    assert len(result["cut_recommendations"]["options"]) == 5
    assert result["cut_recommendations"]["primary"] is not None
    assert card_path.exists()
    assert manifest_path.exists()

    with Image.open(card_path) as card:
        assert card.size == (1080, 1920)
        assert card.format == "PNG"

    result_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
