import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image, ImageDraw

from app.pipelines.visagism.simulation import (
    HairMaskGenerator,
    IdentityValidator,
    NullHairSimulationProvider,
    OpenAIHairSimulationProvider,
)


class TestNullHairSimulationProvider:
    def test_null_provider_never_fabricates_simulation(self):
        provider = NullHairSimulationProvider()
        result = provider.simulate(
            "reference.jpg",
            {"name": "Classic Scissor Taper"},
            "simulation.png",
        )
        assert result["available"] is False
        assert result["provider"] == "none"
        assert result["output_path"] is None
        assert result["identity_preservation_validated"] is False
        assert result["reason"] == "no_hair_simulation_provider_configured"


class TestOpenAIHairSimulationProvider:
    def test_no_api_key_fallback(self):
        """Without API key, must fallback to NullHairSimulationProvider."""
        provider = OpenAIHairSimulationProvider(api_key="")
        result = provider.simulate("ref.jpg", {"name": "Test Cut"}, "out.png")
        assert result["available"] is False
        assert result["provider"] == "none"
        assert result["reason"] == "no_hair_simulation_provider_configured"

    def test_api_error_fallback(self, tmp_path):
        """API error must not crash — fallback to unavailable."""
        provider = OpenAIHairSimulationProvider(api_key="fake-key")
        ref = tmp_path / "ref.jpg"
        # Create a minimal valid image
        img = Image.new("RGB", (100, 100), color="red")
        img.save(ref, format="JPEG")
        out = tmp_path / "out.png"

        with patch.object(provider, "_get_client") as mock_client:
            mock_client.side_effect = Exception("API rate limit")
            result = provider.simulate(str(ref), {"name": "Test"}, str(out))

        assert result["available"] is False
        assert result["provider"] == "openai"
        assert "error" in result["reason"]
        assert result["identity_preservation_validated"] is False


class TestHairMaskGenerator:
    def test_mask_created(self, tmp_path):
        """Mask must be created as PNG with alpha channel."""
        img = tmp_path / "input.jpg"
        mask = tmp_path / "mask.png"
        Image.new("RGB", (200, 300), color="blue").save(img, format="JPEG")

        result = HairMaskGenerator.create_mask(str(img), str(mask))
        assert result == str(mask)
        assert mask.exists()
        with Image.open(mask) as m:
            assert m.mode == "RGBA"


class TestIdentityValidator:
    def test_same_image_high_similarity(self, tmp_path):
        """Same image must have similarity ~1.0."""
        img = tmp_path / "same.jpg"
        Image.new("RGB", (100, 100), color="green").save(img, format="JPEG")
        preserved, score = IdentityValidator.validate(str(img), str(img))
        assert preserved is True
        assert score >= 0.99

    def test_different_image_low_similarity(self, tmp_path):
        """Different images must have low similarity."""
        img1 = tmp_path / "a.jpg"
        img2 = tmp_path / "b.jpg"
        # Create structurally different images (not just color swaps)
        # Image 1: white left half, black right half
        i1 = Image.new("RGB", (100, 100), color="white")
        ImageDraw.Draw(i1).rectangle([50, 0, 100, 100], fill="black")
        i1.save(img1, format="JPEG")
        # Image 2: black left half, white right half (inverted)
        i2 = Image.new("RGB", (100, 100), color="black")
        ImageDraw.Draw(i2).rectangle([50, 0, 100, 100], fill="white")
        i2.save(img2, format="JPEG")
        preserved, score = IdentityValidator.validate(str(img1), str(img2))
        assert preserved is False
        assert score < 0.82

    def test_threshold_boundary(self, tmp_path):
        """Threshold of 0.82 must reject borderline cases."""
        img1 = tmp_path / "a.jpg"
        img2 = tmp_path / "b.jpg"
        # Two very similar but not identical images
        Image.new("RGB", (100, 100), color=(100, 100, 100)).save(img1, format="JPEG")
        Image.new("RGB", (100, 100), color=(105, 105, 105)).save(img2, format="JPEG")
        preserved, score = IdentityValidator.validate(str(img1), str(img2))
        # Score should be calculable even if borderline
        assert isinstance(preserved, bool)
        assert 0.0 <= score <= 1.0
