import base64
import io

import numpy as np
import pytest
from PIL import Image

from app.ai.visagism.providers.fal_renderer import (
    FalOverlayRenderer,
    SimulationProviderError,
)


def _png_data_uri() -> str:
    image = Image.new("RGB", (4, 4), (12, 34, 56))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


class FakeResponse:
    def __init__(self, status_code=200, data=None):
        self.status_code = status_code
        self._data = data or {}
        self.content = b""

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"http-{self.status_code}")

    def json(self):
        return self._data


class FakeClient:
    def __init__(self, response):
        self.response = response
        self.last_post = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def post(self, url, headers=None, json=None):
        self.last_post = {"url": url, "headers": headers, "json": json}
        return self.response

    def get(self, *args, **kwargs):
        raise AssertionError("data URI output should not require an image GET")


def test_fal_renderer_returns_image_and_sends_masked_inpainting_request():
    client = FakeClient(FakeResponse(data={"images": [{"url": _png_data_uri()}]}))
    renderer = FalOverlayRenderer(
        api_key="test-key",
        model="fal-ai/flux-general/inpainting",
        client_factory=lambda **_: client,
    )
    original = Image.new("RGB", (4, 4), (1, 2, 3))
    mask = np.zeros((4, 4), dtype=np.uint8)
    mask[0:2, :] = 255

    result = renderer.render(
        init_image=original,
        reference_image=original,
        mask=mask,
        edit_instruction="hair only",
        denoising=0.30,
        identity_weight=0.90,
    )

    assert isinstance(result, Image.Image)
    assert result.size == original.size
    assert client.last_post["url"].endswith("fal-ai/flux-general/inpainting")
    assert client.last_post["json"]["image_url"].startswith("data:image/png;base64,")
    assert client.last_post["json"]["mask_url"].startswith("data:image/png;base64,")
    assert client.last_post["json"]["strength"] == 0.30


def test_fal_renderer_fails_closed_when_key_is_missing():
    renderer = FalOverlayRenderer(api_key="", model="model")
    original = Image.new("RGB", (2, 2))

    with pytest.raises(SimulationProviderError, match="inpaint_provider_not_configured"):
        renderer.render(
            init_image=original,
            reference_image=original,
            mask=np.ones((2, 2), dtype=np.uint8),
            edit_instruction="hair",
            denoising=0.30,
            identity_weight=0.90,
        )


def test_fal_renderer_maps_rate_limit_to_stable_reason():
    client = FakeClient(FakeResponse(status_code=429))
    renderer = FalOverlayRenderer(
        api_key="test-key",
        model="model",
        client_factory=lambda **_: client,
    )
    original = Image.new("RGB", (2, 2))

    with pytest.raises(SimulationProviderError) as exc:
        renderer.render(
            init_image=original,
            reference_image=original,
            mask=np.ones((2, 2), dtype=np.uint8),
            edit_instruction="hair",
            denoising=0.30,
            identity_weight=0.90,
        )
    assert exc.value.reason_code == "provider_rate_limited"


def test_fal_renderer_rejects_reference_object_mismatch():
    renderer = FalOverlayRenderer(api_key="test-key", model="model")
    original = Image.new("RGB", (2, 2))

    with pytest.raises(SimulationProviderError) as exc:
        renderer.render(
            init_image=original,
            reference_image=original.copy(),
            mask=np.ones((2, 2), dtype=np.uint8),
            edit_instruction="hair",
            denoising=0.30,
            identity_weight=0.90,
        )
    assert exc.value.reason_code == "provider_reference_mismatch"
