from app.ai.visagism.masked_overlay_pipeline import MaskedOverlayPipeline


class MaskOK:
    def build_hair_mask(self, original_photo):
        return {
            "valid": True,
            "mask": "hair-mask",
            "protected_regions_touched": False,
            "beard_enabled": False,
            "background_locked": True,
            "mask_kind": "hair-only-test",
            "coverage_ratio": 0.2,
        }


class MaskBad:
    def build_hair_mask(self, original_photo):
        return {
            "valid": True,
            "mask": "bad-mask",
            "protected_regions_touched": True,
            "beard_enabled": False,
            "background_locked": True,
        }


class MaskWithBeard:
    def build_hair_mask(self, original_photo):
        return {
            "valid": True,
            "mask": "unsafe-mask",
            "protected_regions_touched": False,
            "beard_enabled": True,
            "background_locked": True,
        }


class MaskWithoutBackgroundLock:
    def build_hair_mask(self, original_photo):
        return {
            "valid": True,
            "mask": "unsafe-mask",
            "protected_regions_touched": False,
            "beard_enabled": False,
            "background_locked": False,
        }


class Renderer:
    def __init__(self):
        self.last = None

    def render(self, **kwargs):
        self.last = kwargs
        return "candidate.jpg"


class Verifier:
    def __init__(self, scores):
        self.scores = iter(scores)

    def compare(self, candidate, reference):
        return next(self.scores)


def test_renderer_receives_original_as_init_and_reference():
    renderer = Renderer()
    result = MaskedOverlayPipeline(MaskOK(), renderer, Verifier([0.91, 0.92, 0.93])).run(
        original_photo="original.jpg",
        real_reference_photos=["r1", "r2", "r3"],
        edit_instruction="change only hair",
    )
    assert result["mode"] == "hair_overlay"
    assert result["editableRegions"] == ["hair"]
    assert renderer.last["init_image"] == "original.jpg"
    assert renderer.last["reference_image"] == "original.jpg"
    assert renderer.last["mask"] == "hair-mask"


def test_low_identity_score_returns_original_photo():
    result = MaskedOverlayPipeline(MaskOK(), Renderer(), Verifier([0.95, 0.79, 0.94])).run(
        original_photo="original.jpg",
        real_reference_photos=["r1", "r2", "r3"],
        edit_instruction="hair only",
    )
    assert result == {
        "image": "original.jpg",
        "mode": "original_plus_spec",
        "simulationApplied": False,
        "reason": "identity_lock_failed",
        "baseImagePreserved": True,
        "identity_scores": [0.95, 0.79, 0.94],
    }


def test_mask_touching_protected_region_is_blocked_before_render():
    renderer = Renderer()
    result = MaskedOverlayPipeline(MaskBad(), renderer, Verifier([0.99, 0.99, 0.99])).run(
        original_photo="original.jpg",
        real_reference_photos=["r1", "r2", "r3"],
        edit_instruction="hair only",
    )
    assert result["image"] == "original.jpg"
    assert result["reason"] == "protected_region_in_mask"
    assert renderer.last is None


def test_haircut_pipeline_refuses_beard_region():
    renderer = Renderer()
    result = MaskedOverlayPipeline(MaskWithBeard(), renderer, Verifier([])).run(
        original_photo="original.jpg",
        real_reference_photos=["r1", "r2", "r3"],
        edit_instruction="hair only",
    )
    assert result["reason"] == "beard_region_not_allowed"
    assert renderer.last is None


def test_haircut_pipeline_requires_background_lock():
    renderer = Renderer()
    result = MaskedOverlayPipeline(MaskWithoutBackgroundLock(), renderer, Verifier([])).run(
        original_photo="original.jpg",
        real_reference_photos=["r1", "r2", "r3"],
        edit_instruction="hair only",
    )
    assert result["reason"] == "background_lock_not_confirmed"
    assert renderer.last is None


def test_requires_three_to_five_real_references():
    result = MaskedOverlayPipeline(MaskOK(), Renderer(), Verifier([])).run(
        original_photo="original.jpg",
        real_reference_photos=["r1", "r2"],
        edit_instruction="hair only",
    )
    assert result["mode"] == "original_plus_spec"
    assert result["reason"] == "invalid_reference_count"


def test_unsafe_generation_settings_are_blocked():
    pipeline = MaskedOverlayPipeline(MaskOK(), Renderer(), Verifier([]))
    assert pipeline.run(
        original_photo="original.jpg",
        real_reference_photos=["1", "2", "3"],
        edit_instruction="hair",
        denoising=0.60,
    )["reason"] == "unsafe_denoising"
    assert pipeline.run(
        original_photo="original.jpg",
        real_reference_photos=["1", "2", "3"],
        edit_instruction="hair",
        identity_weight=0.50,
    )["reason"] == "identity_weight_too_low"
