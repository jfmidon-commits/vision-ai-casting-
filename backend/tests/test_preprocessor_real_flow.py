from pathlib import Path

import pytest

from app.ai.preprocessing.preprocessor import ImagePreprocessor, PreprocessedPhoto


@pytest.mark.asyncio
async def test_preprocessor_preserves_visagism_metadata():
    image_path = Path("tests/fixtures/visagism/dataset_001/01_frontal_neutra_close.jpg")
    preprocessor = ImagePreprocessor()

    result = await preprocessor.process_single(
        {
            "id": "photo-1",
            "url": str(image_path),
            "angle": "front",
            "quality_score": 0.95,
            "is_usable": True,
        }
    )

    assert isinstance(result, PreprocessedPhoto)
    assert result["id"] == "photo-1"
    assert result.id == "photo-1"
    assert result.url == str(image_path)
    assert result.angle == "front"
    assert result.quality_score == 0.95
    assert result.is_usable is True
    assert result.image.width > 0
    assert result.image.height > 0


@pytest.mark.asyncio
async def test_preprocessor_batch_uses_asyncio_and_keeps_urls():
    image_path = Path("tests/fixtures/visagism/dataset_001/01_frontal_neutra_close.jpg")
    preprocessor = ImagePreprocessor()

    results = await preprocessor.process_batch(
        [
            {"id": "a", "url": str(image_path), "angle": "front"},
            {"id": "b", "url": str(image_path), "angle": "front_smiling"},
        ]
    )

    assert len(results) == 2
    assert results[0].url == str(image_path)
    assert results[1].angle == "front_smiling"
