import numpy as np
from PIL import Image

from app.ai.visagism.masked_overlay_pipeline import MaskedOverlayPipeline


class CountingMask:
    def __init__(self):
        self.calls = 0

    def build_hair_mask(self, original_photo):
        self.calls += 1
        mask = np.ones((4, 4), dtype=np.uint8) * 255
        return {
            "valid": True,
            "mask": mask,
            "protected_regions_touched": False,
            "beard_enabled": False,
            "background_locked": True,
            "mask_kind": "test",
            "coverage_ratio": 0.2,
        }


class EchoRenderer:
    def render(self, **kwargs):
        return kwargs["init_image"]


class AlwaysSameVerifier:
    def compare(self, candidate, reference):
        return 1.0


def test_pipeline_reuses_prevalidated_mask_without_rebuilding():
    adapter = CountingMask()
    original = Image.new("RGB", (4, 4), "black")
    validated = adapter.build_hair_mask(original)
    pipeline = MaskedOverlayPipeline(
        mask_adapter=adapter,
        renderer=EchoRenderer(),
        verifier=AlwaysSameVerifier(),
    )
    result = pipeline.run(
        original_photo=original,
        real_reference_photos=[original, original.copy(), original.copy()],
        edit_instruction="hair only",
        validated_mask_result=validated,
    )
    assert result["simulationApplied"] is True
    assert adapter.calls == 1
