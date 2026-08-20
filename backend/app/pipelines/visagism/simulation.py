"""Provider-neutral interface for optional hairstyle simulation."""

from __future__ import annotations

import logging
import os
import tempfile
from abc import ABC, abstractmethod
from typing import Any, Dict, Mapping, Optional, Tuple

from PIL import Image, ImageDraw, ImageFilter

logger = logging.getLogger(__name__)


class HairSimulationProvider(ABC):
    """Contract for optional external or local hairstyle simulation providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Stable provider identifier."""
        raise NotImplementedError

    @abstractmethod
    def simulate(
        self,
        reference_image_path: str,
        recommendation: Mapping[str, Any],
        output_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create or request a simulation without changing pipeline evidence."""
        raise NotImplementedError


class NullHairSimulationProvider(HairSimulationProvider):
    """Default provider that explicitly reports simulation as unavailable."""

    @property
    def name(self) -> str:
        return "none"

    def simulate(
        self,
        reference_image_path: str,
        recommendation: Mapping[str, Any],
        output_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        return {
            "available": False,
            "provider": self.name,
            "reference_image": reference_image_path,
            "output_path": None,
            "reason": "no_hair_simulation_provider_configured",
            "identity_preservation_validated": False,
        }


class HairMaskGenerator:
    """Generate a hair mask for inpainting using heuristics."""

    @staticmethod
    def create_mask(image_path: str, output_mask_path: str) -> str:
        """
        Create a mask where hair region is transparent (alpha=0).
        Uses a simple heuristic: top 40% of image + side regions.
        """
        with Image.open(image_path).convert("RGBA") as img:
            width, height = img.size

            # Define hair region: top 45% + sides
            top_region = int(height * 0.45)
            side_margin = int(width * 0.15)

            draw = Image.new("L", (width, height), 0)
            d = ImageDraw.Draw(draw)

            # Main hair region (top + sides)
            d.rectangle([side_margin, 0, width - side_margin, top_region], fill=255)
            # Side regions extending down
            d.rectangle([0, 0, side_margin, int(height * 0.6)], fill=255)
            d.rectangle([width - side_margin, 0, width, int(height * 0.6)], fill=255)

            # Smooth the mask
            mask = draw.filter(ImageFilter.GaussianBlur(radius=15))

            # Convert to RGBA: white areas become transparent (alpha=0)
            mask_rgba = Image.new("RGBA", (width, height), (0, 0, 0, 255))
            pixels = mask.load()
            mask_pixels = mask_rgba.load()
            for y in range(height):
                for x in range(width):
                    if pixels[x, y] > 128:
                        mask_pixels[x, y] = (0, 0, 0, 0)

            mask_rgba.save(output_mask_path, format="PNG")
            return output_mask_path


class IdentityValidator:
    """Validate identity preservation using perceptual hash."""

    @staticmethod
    def compute_phash(image_path: str) -> str:
        """Compute perceptual hash of an image."""
        with Image.open(image_path) as img:
            # Simple average hash (aHash)
            img = img.convert("L").resize((8, 8), Image.Resampling.LANCZOS)
            pixels = list(img.getdata())
            avg = sum(pixels) / len(pixels)
            bits = "".join("1" if p > avg else "0" for p in pixels)
            return hex(int(bits, 2))[2:].zfill(16)

    @staticmethod
    def similarity(hash1: str, hash2: str) -> float:
        """Compute similarity between two hashes (0-1)."""
        if len(hash1) != len(hash2):
            return 0.0
        # Hamming distance
        h1 = int(hash1, 16)
        h2 = int(hash2, 16)
        x = h1 ^ h2
        distance = bin(x).count("1")
        return 1.0 - (distance / 64.0)

    @classmethod
    def validate(cls, original_path: str, simulated_path: str, threshold: float = 0.82) -> Tuple[bool, float]:
        """Validate that identity is preserved."""
        try:
            hash1 = cls.compute_phash(original_path)
            hash2 = cls.compute_phash(simulated_path)
            sim = cls.similarity(hash1, hash2)
            return sim >= threshold, sim
        except Exception:
            return False, 0.0


class OpenAIHairSimulationProvider(HairSimulationProvider):
    """Real hairstyle simulation using OpenAI Image Edit API."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-image-1.5"):
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self._model = model
        self._client = None

    @property
    def name(self) -> str:
        return "openai"

    def _get_client(self):
        if self._client is None:
            import openai
            self._client = openai.OpenAI(api_key=self._api_key)
        return self._client

    def simulate(
        self,
        reference_image_path: str,
        recommendation: Mapping[str, Any],
        output_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate a hairstyle simulation using OpenAI Image Edit API.
        Falls back to NullHairSimulationProvider on any error.
        """
        if not self._api_key:
            return NullHairSimulationProvider().simulate(
                reference_image_path, recommendation, output_path
            )

        if output_path is None:
            output_path = os.path.join(
                tempfile.gettempdir(), f"simulation_{os.urandom(4).hex()}.png"
            )

        try:
            # Generate mask
            mask_path = output_path.replace(".png", "_mask.png")
            HairMaskGenerator.create_mask(reference_image_path, mask_path)

            # Build prompt
            name = recommendation.get("name", "the recommended haircut")
            fade = recommendation.get("fade", "")
            top = recommendation.get("top_cm", [])
            sides = recommendation.get("sides_mm", [])
            direction = recommendation.get("direction", "")
            finish = recommendation.get("finish", "")

            spec_parts = [f"{name}"]
            if top:
                spec_parts.append(
                    f"top {top[0]}-{top[-1]}cm" if len(top) > 1 else f"top {top[0]}cm"
                )
            if sides:
                spec_parts.append(
                    f"sides {sides[0]}-{sides[-1]}mm"
                    if len(sides) > 1
                    else f"sides {sides[0]}mm"
                )
            if fade:
                spec_parts.append(fade)
            if direction:
                spec_parts.append(f"{direction} direction")
            if finish:
                spec_parts.append(f"{finish} finish")

            prompt = (
                f"Change ONLY the hairstyle to: {', '.join(spec_parts)}. "
                f"Keep the exact same face, eyes, eyebrows, beard, expression, skin tone, "
                f"lighting, and background. Do not alter any facial features. Hair only."
            )

            # Call OpenAI Image Edit API
            client = self._get_client()
            with open(reference_image_path, "rb") as img_file, open(
                mask_path, "rb"
            ) as mask_file:
                response = client.images.edit(
                    image=img_file,
                    mask=mask_file,
                    prompt=prompt,
                    n=1,
                    size="1024x1024",
                    input_fidelity="high",
                )

            # Download result
            if response.data and response.data[0].url:
                import httpx

                image_url = response.data[0].url
                with httpx.Client(timeout=30.0) as http_client:
                    image_response = http_client.get(image_url)
                    image_response.raise_for_status()
                    with open(output_path, "wb") as f:
                        f.write(image_response.content)
            else:
                return {
                    "available": False,
                    "provider": self.name,
                    "reference_image": reference_image_path,
                    "output_path": None,
                    "reason": "openai_no_image_returned",
                    "identity_preservation_validated": False,
                }

            # Validate identity preservation
            preserved, similarity = IdentityValidator.validate(
                reference_image_path, output_path
            )

            if not preserved:
                if os.path.exists(output_path):
                    os.remove(output_path)
                return {
                    "available": False,
                    "provider": self.name,
                    "reference_image": reference_image_path,
                    "output_path": None,
                    "reason": f"identity_not_preserved_similarity_{similarity:.2f}",
                    "identity_preservation_validated": False,
                    "similarity_score": similarity,
                }

            return {
                "available": True,
                "provider": self.name,
                "reference_image": reference_image_path,
                "output_path": output_path,
                "reason": "success",
                "identity_preservation_validated": True,
                "similarity_score": similarity,
                "prompt": prompt,
            }

        except Exception as exc:
            logger.warning(f"Hair simulation failed: {exc}")
            if os.path.exists(output_path):
                os.remove(output_path)
            return {
                "available": False,
                "provider": self.name,
                "reference_image": reference_image_path,
                "output_path": None,
                "reason": f"error_{exc.__class__.__name__}_{str(exc)[:100]}",
                "identity_preservation_validated": False,
            }
