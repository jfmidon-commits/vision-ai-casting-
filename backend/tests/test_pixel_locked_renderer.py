import numpy as np

from app.ai.visagism.pixel_locked_renderer import (
    PixelLockedRenderer,
    compose_only_masked_pixels,
)


class EvilRenderer:
    def render(self, **kwargs):
        original = kwargs["init_image"]
        # Simulates a generator attempting to replace the entire person/image.
        return np.full_like(original, 255)


def test_compose_changes_only_masked_pixels():
    original = np.zeros((4, 4, 3), dtype=np.uint8)
    candidate = np.full((4, 4, 3), 255, dtype=np.uint8)
    mask = np.zeros((4, 4), dtype=np.uint8)
    mask[1:3, 1:3] = 255

    out = compose_only_masked_pixels(original, candidate, mask)

    # Allowed area receives rendered pixels.
    assert np.all(out[1:3, 1:3] == 255)
    # Every pixel outside the mask remains exactly the original.
    outside = mask == 0
    assert np.array_equal(out[outside], original[outside])


def test_renderer_cannot_replace_face_body_or_background_outside_mask():
    original = np.zeros((6, 6, 3), dtype=np.uint8)
    mask = np.zeros((6, 6), dtype=np.uint8)
    # Tiny synthetic 'hair' area at the top only.
    mask[0:2, 2:4] = 255

    renderer = PixelLockedRenderer(EvilRenderer())
    out = renderer.render(
        init_image=original,
        reference_image=original,
        mask=mask,
        edit_instruction="change hair only",
        denoising=0.30,
        identity_weight=0.90,
    )

    assert np.all(out[0:2, 2:4] == 255)
    outside = mask == 0
    assert np.array_equal(out[outside], original[outside])


def test_rejects_different_reference_object():
    original = np.zeros((2, 2, 3), dtype=np.uint8)
    different_object_same_pixels = original.copy()
    mask = np.ones((2, 2), dtype=np.uint8) * 255
    renderer = PixelLockedRenderer(EvilRenderer())

    try:
        renderer.render(
            init_image=original,
            reference_image=different_object_same_pixels,
            mask=mask,
            edit_instruction="hair",
            denoising=0.30,
            identity_weight=0.90,
        )
    except ValueError as exc:
        assert "exact original" in str(exc)
    else:
        raise AssertionError("different reference object should be rejected")
