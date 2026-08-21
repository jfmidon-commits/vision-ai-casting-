"""Pixel-level identity protection for visagism renders.

The delegate renderer may return any edited image, but only pixels explicitly
allowed by the hair/beard mask are copied back onto the untouched original.
Everything outside the mask is taken byte-for-byte from the original image.
"""
from dataclasses import dataclass
from typing import Any

import numpy as np
from PIL import Image


def _to_array(image: Any) -> np.ndarray:
    if isinstance(image, np.ndarray):
        return image.copy()
    if isinstance(image, Image.Image):
        return np.asarray(image).copy()
    raise TypeError("pixel lock requires numpy arrays or PIL images")


def _mask_to_bool(mask: Any, height: int, width: int) -> np.ndarray:
    arr = _to_array(mask)
    if arr.ndim == 3:
        arr = arr[..., 0]
    if arr.shape != (height, width):
        raise ValueError("mask dimensions must match image dimensions")
    return arr > 0


def compose_only_masked_pixels(original: Any, candidate: Any, mask: Any) -> Any:
    """Return original with candidate pixels copied only where mask is active."""
    original_arr = _to_array(original)
    candidate_arr = _to_array(candidate)
    if original_arr.shape != candidate_arr.shape:
        raise ValueError("candidate dimensions must match original image")

    height, width = original_arr.shape[:2]
    active = _mask_to_bool(mask, height, width)
    output = original_arr.copy()
    output[active] = candidate_arr[active]

    if isinstance(original, Image.Image):
        return Image.fromarray(output.astype(np.uint8), mode=original.mode)
    return output


@dataclass
class PixelLockedRenderer:
    """Wrap a renderer so unmasked pixels can never be changed."""

    delegate: Any

    def render(
        self,
        *,
        init_image: Any,
        reference_image: Any,
        mask: Any,
        edit_instruction: str,
        denoising: float,
        identity_weight: float,
    ) -> Any:
        # Identity safety rule: init and reference must be the same original.
        if reference_image is not init_image:
            # For immutable image objects identity is the strongest fail-closed
            # check. Value-equality is intentionally not used here.
            raise ValueError("reference_image must be the exact original init_image")

        candidate = self.delegate.render(
            init_image=init_image,
            reference_image=reference_image,
            mask=mask,
            edit_instruction=edit_instruction,
            denoising=denoising,
            identity_weight=identity_weight,
        )
        return compose_only_masked_pixels(init_image, candidate, mask)
