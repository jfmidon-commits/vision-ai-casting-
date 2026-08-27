"""Fal.ai inpainting renderer for identity-safe haircut simulation.

The renderer returns only an image object. Publication safety remains the
responsibility of PixelLockedRenderer + IdentityLockPolicy.
"""
from __future__ import annotations

import base64
import io
from typing import Any, Callable, Optional

import httpx
import numpy as np
from PIL import Image


class SimulationProviderError(RuntimeError):
    """Stable provider error carrying a non-sensitive public reason code."""

    def __init__(self, reason_code: str):
        super().__init__(reason_code)
        self.reason_code = reason_code


def _image_to_data_uri(image: Any, *, is_mask: bool = False) -> str:
    if isinstance(image, np.ndarray):
        if is_mask:
            arr = image
            if arr.ndim == 3:
                arr = arr[..., 0]
            pil = Image.fromarray(arr.astype(np.uint8), mode="L")
        else:
            pil = Image.fromarray(image.astype(np.uint8)).convert("RGB")
    elif isinstance(image, Image.Image):
        pil = image.convert("L" if is_mask else "RGB")
    else:
        raise SimulationProviderError("provider_invalid_image_input")

    buffer = io.BytesIO()
    pil.save(buffer, format="PNG")
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

    The selected default endpoint supports image_url + mask_url + strength.
    Requests are synchronous on purpose: the API route owns idempotency and
    does not auto-retry POST generation requests.
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout_seconds: float = 120.0,
        client_factory: Callable[..., Any] = httpx.Client,
    ) -> None:
        self.api_key = api_key.strip()
        self.model = model.strip()
        self.timeout_seconds = float(timeout_seconds)
        self.client_factory = client_factory

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.model)

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

        payload = {
            "prompt": edit_instruction,
            "image_url": _image_to_data_uri(init_image),
            "mask_url": _image_to_data_uri(mask, is_mask=True),
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
                return image.convert("RGB").copy()
        except Exception as exc:
            raise SimulationProviderError("provider_invalid_output") from exc
