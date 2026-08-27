"""Fal.ai inpainting renderer for identity-safe haircut simulation.

The provider works on a bounded-resolution copy for predictable cost/latency.
The generated hair candidate is restored to the exact source dimensions before
PixelLockedRenderer composites it over the immutable full-resolution original.
"""

from __future__ import annotations

import base64
import io
import math
from typing import Any, Callable, Optional, Tuple

import httpx
import numpy as np
from PIL import Image


class SimulationProviderError(RuntimeError):
    """Stable provider error carrying a non-sensitive public reason code."""

    def __init__(self, reason_code: str):
        super().__init__(reason_code)
        self.reason_code = reason_code


def _to_rgb_image(image: Any) -> Image.Image:
    if isinstance(image, np.ndarray):
        if image.ndim != 3 or image.shape[2] < 3:
            raise SimulationProviderError("provider_invalid_image_input")
        return Image.fromarray(image[..., :3].astype(np.uint8)).convert("RGB")
    if isinstance(image, Image.Image):
        return image.convert("RGB").copy()
    raise SimulationProviderError("provider_invalid_image_input")


def _to_mask_image(mask: Any, expected_size: Tuple[int, int]) -> Image.Image:
    if isinstance(mask, np.ndarray):
        arr = mask[..., 0] if mask.ndim == 3 else mask
        if arr.ndim != 2:
            raise SimulationProviderError("provider_invalid_image_input")
        image = Image.fromarray(arr.astype(np.uint8), mode="L")
    elif isinstance(mask, Image.Image):
        image = mask.convert("L").copy()
    else:
        raise SimulationProviderError("provider_invalid_image_input")
    if image.size != expected_size:
        raise SimulationProviderError("provider_mask_size_mismatch")
    return image


def _working_size(width: int, height: int, max_pixels: int) -> Tuple[int, int]:
    if width <= 0 or height <= 0 or max_pixels <= 0:
        raise SimulationProviderError("provider_invalid_image_input")
    if width * height <= max_pixels:
        return width, height

    scale = math.sqrt(max_pixels / float(width * height))
    working_width = max(8, int(width * scale))
    working_height = max(8, int(height * scale))

    # Flux image endpoints behave most predictably on dimensions divisible by
    # eight. Round down so the configured pixel budget is never exceeded.
    working_width = max(8, (working_width // 8) * 8)
    working_height = max(8, (working_height // 8) * 8)
    return working_width, working_height


def _image_to_data_uri(image: Image.Image) -> str:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _decode_data_uri(value: str) -> bytes:
    try:
        _, encoded = value.split(",", 1)
        return base64.b64decode(encoded)
    except Exception as exc:
        raise SimulationProviderError("provider_invalid_output") from exc


class FalOverlayRenderer:
    """Call a mask-aware Fal image-edit endpoint and return a PIL image.

    Requests are synchronous on purpose: the API route owns idempotency and
    never retries a generation POST automatically.
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout_seconds: float = 120.0,
        max_pixels: int = 1_048_576,
        client_factory: Callable[..., Any] = httpx.Client,
    ) -> None:
        self.api_key = api_key.strip()
        self.model = model.strip()
        self.timeout_seconds = float(timeout_seconds)
        self.max_pixels = int(max_pixels)
        self.client_factory = client_factory

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.model and self.max_pixels > 0)

    def render(
        self,
        *,
        init_image: Any,
        reference_image: Any,
        mask: Any,
        edit_instruction: str,
        denoising: float,
        identity_weight: float,
    ) -> Image.Image:
        del identity_weight  # enforced by the local identity gate, not Fal.
        if not self.configured:
            raise SimulationProviderError("inpaint_provider_not_configured")
        if reference_image is not init_image:
            raise SimulationProviderError("provider_reference_mismatch")

        original = _to_rgb_image(init_image)
        original_size = original.size
        mask_image = _to_mask_image(mask, original_size)
        work_size = _working_size(
            original_size[0], original_size[1], self.max_pixels
        )

        if work_size != original_size:
            work_image = original.resize(work_size, Image.Resampling.LANCZOS)
            work_mask = mask_image.resize(work_size, Image.Resampling.NEAREST)
        else:
            work_image = original
            work_mask = mask_image

        payload = {
            "prompt": edit_instruction,
            "image_url": _image_to_data_uri(work_image),
            "mask_url": _image_to_data_uri(work_mask),
            "image_size": {"width": work_size[0], "height": work_size[1]},
            "strength": float(denoising),
            "num_images": 1,
            "enable_safety_checker": True,
            "output_format": "png",
        }
        headers = {
            "Authorization": f"Key {self.api_key}",
            "Content-Type": "application/json",
        }
        endpoint = f"https://fal.run/{self.model}"

        try:
            with self.client_factory(timeout=self.timeout_seconds) as client:
                response = client.post(endpoint, headers=headers, json=payload)
                if response.status_code == 429:
                    raise SimulationProviderError("provider_rate_limited")
                if response.status_code in (401, 403):
                    raise SimulationProviderError("provider_auth_failed")
                if response.status_code >= 500:
                    raise SimulationProviderError("provider_unavailable")
                response.raise_for_status()
                data = response.json()
                images = data.get("images") if isinstance(data, dict) else None
                if not isinstance(images, list) or not images:
                    raise SimulationProviderError("provider_empty_output")

                first = images[0]
                output_url: Optional[str]
                if isinstance(first, dict):
                    output_url = first.get("url")
                elif isinstance(first, str):
                    output_url = first
                else:
                    output_url = None
                if not output_url:
                    raise SimulationProviderError("provider_empty_output")

                if output_url.startswith("data:"):
                    raw = _decode_data_uri(output_url)
                else:
                    image_response = client.get(output_url, timeout=30.0)
                    image_response.raise_for_status()
                    raw = image_response.content
        except SimulationProviderError:
            raise
        except httpx.TimeoutException as exc:
            raise SimulationProviderError("provider_timeout") from exc
        except httpx.HTTPError as exc:
            raise SimulationProviderError("provider_request_failed") from exc
        except Exception as exc:
            raise SimulationProviderError("provider_invalid_output") from exc

        try:
            with Image.open(io.BytesIO(raw)) as image:
                generated = image.convert("RGB").copy()
        except Exception as exc:
            raise SimulationProviderError("provider_invalid_output") from exc

        if generated.size != work_size:
            raise SimulationProviderError("provider_output_size_mismatch")
        if work_size != original_size:
            generated = generated.resize(original_size, Image.Resampling.LANCZOS)
        return generated
