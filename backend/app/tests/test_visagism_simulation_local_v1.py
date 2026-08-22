import sys
from unittest.mock import patch

import numpy as np
from PIL import Image

from app.ai.visagism.adapters.deepface_identity import DeepFaceArcFaceVerifier
from app.ai.visagism.adapters.mediapipe_hair_mask import MediaPipeHairBeardMaskAdapter
from app.ai.visagism.simulation_service import VisagismSimulationService


def _synthetic_landmarks():
    points = [(0.5, 0.5) for _ in range(468)]
    oval = MediaPipeHairBeardMaskAdapter.FACE_OVAL
    # Deterministic face oval spanning x=.30-.70 and y=.35-.80.
    theta = np.linspace(0, 2 * np.pi, len(oval), endpoint=False)
    for idx, angle in zip(oval, theta):
        x = 0.5 + 0.20 * np.cos(angle)
        y = 0.575 + 0.225 * np.sin(angle)
        points[idx] = (float(x), float(y))
    return points


def _synthetic_landmarks_with_protected_overlap():
    points = _synthetic_landmarks()
    # Put the left eyebrow polygon inside the candidate hair ROI so the
    # protected-region gate must reject the mask.
    eyebrow = MediaPipeHairBeardMaskAdapter.LEFT_EYEBROW
    xs = np.linspace(0.40, 0.60, len(eyebrow))
    ys = [0.28, 0.27, 0.28, 0.29, 0.30, 0.31, 0.32, 0.31, 0.30, 0.29]
    for idx, x, y in zip(eyebrow, xs, ys):
        points[idx] = (float(x), float(y))
    return points


def _image(value=80):
    return Image.fromarray(np.full((200, 200, 3), value, dtype=np.uint8), mode="RGB")


class AlwaysPassVerifier:
    def compare(self, candidate, reference):
        return 0.90


class FullFrameRenderer:
    def render(
        self,
        *,
        init_image,
        reference_image,
        mask,
        edit_instruction,
        denoising,
        identity_weight,
    ):
        arr = np.asarray(init_image).copy()
        arr[:] = 255
        return Image.fromarray(arr, mode="RGB")


def test_mask_adapter_builds_conservative_hair_roi():
    adapter = MediaPipeHairBeardMaskAdapter(detector=lambda _img: _synthetic_landmarks())
    result = adapter.build_hair_beard_mask(_image())

    assert result["valid"] is True
    assert result["protected_regions_touched"] is False
    assert result["beard_enabled"] is False
    assert 0.03 <= result["coverage_ratio"] <= 0.45
    assert result["mask"].shape == (200, 200)


def test_mask_adapter_fails_closed_without_face():
    adapter = MediaPipeHairBeardMaskAdapter(detector=lambda _img: None)
    result = adapter.build_hair_beard_mask(_image())

    assert result["valid"] is False
    assert result["reason"] == "face_not_detected"
    assert int(result["mask"].sum()) == 0


def test_mask_adapter_blocks_coverage_out_of_range():
    adapter = MediaPipeHairBeardMaskAdapter(
        detector=lambda _img: _synthetic_landmarks(),
        coverage_max=0.01,
    )
    result = adapter.build_hair_beard_mask(_image())

    assert result["valid"] is False
    assert result["reason"] == "hair_roi_coverage_out_of_range"
    assert result["calibration_status"] == "provisional"
    assert result["coverage_ratio"] > adapter.coverage_max


def test_mask_adapter_blocks_protected_region_overlap():
    adapter = MediaPipeHairBeardMaskAdapter(
        detector=lambda _img: _synthetic_landmarks_with_protected_overlap()
    )
    result = adapter.build_hair_beard_mask(_image())

    assert result["valid"] is False
    assert result["reason"] == "protected_region_in_mask"
    assert result["protected_regions_touched"] is True
    assert result["protected_overlap_ratio"] > adapter.protected_overlap_max


def test_arcface_normalization_preserves_native_boundary():
    verifier = DeepFaceArcFaceVerifier()

    assert verifier.normalize_distance(0.0) == 1.0
    assert abs(verifier.normalize_distance(0.68) - 0.80) < 1e-9
    assert verifier.normalize_distance(0.34) > 0.80
    assert verifier.normalize_distance(0.85) < 0.80


def test_arcface_adapter_uses_native_threshold_and_is_fail_closed():
    verifier = DeepFaceArcFaceVerifier(
        verify_func=lambda _candidate, _reference: {
            "distance": 0.34,
            "threshold": 0.68,
            "verified": True,
        }
    )
    details = verifier.compare_with_details(_image(), _image())
    assert details["native_verified"] is True
    assert details["normalized_identity_score"] > 0.80
    assert details["score_semantics"] == "normalized_decision_score_not_biometric_similarity"

    failing = DeepFaceArcFaceVerifier(
        verify_func=lambda *_args: (_ for _ in ()).throw(RuntimeError("boom"))
    )
    assert failing.compare(_image(), _image()) == 0.0


def test_arcface_missing_deepface_dependency_fails_closed():
    verifier = DeepFaceArcFaceVerifier()
    with patch.dict(sys.modules, {"deepface": None}):
        details = verifier.compare_with_details(_image(), _image())

    assert details["normalized_identity_score"] == 0.0
    assert details["native_verified"] is False
    assert details["reason"] == "identity_verification_failed"


def test_service_without_provider_is_blocked_and_card_shows_original():
    original = _image(70)
    refs = [_image(71), _image(72), _image(73)]
    adapter = MediaPipeHairBeardMaskAdapter(detector=lambda _img: _synthetic_landmarks())
    service = VisagismSimulationService(mask_adapter=adapter, verifier=AlwaysPassVerifier())

    result = service.simulate(
        original_photo=original,
        real_reference_photos=refs,
        source_photos=[{"image": original}, *({"image": ref} for ref in refs)],
        preferred_original=original,
        edit_instruction="short textured crop",
    )

    assert result["simulation_status"] == "blocked"
    assert result["reason"] == "inpaint_provider_not_configured"
    assert result["card_media"]["simulationApplied"] is False
    assert result["card_media"]["displayImage"] is original
    assert result["card_media"]["displayMode"] == "original_plus_spec"


def test_service_not_requested_keeps_original_card_media():
    original = _image(70)
    service = VisagismSimulationService(
        mask_adapter=MediaPipeHairBeardMaskAdapter(detector=lambda _img: None),
        verifier=AlwaysPassVerifier(),
    )

    result = service.not_requested(
        source_photos=[{"image": original}],
        preferred_original=original,
    )

    assert result["simulation_status"] == "not_requested"
    assert result["reason"] is None
    assert result["card_media"]["simulationApplied"] is False
    assert result["card_media"]["displayImage"] is original
    assert result["card_media"]["displayMode"] == "original"


def test_service_blocks_invalid_reference_count_before_generation():
    original = _image(70)
    refs = [_image(71), _image(72)]
    adapter = MediaPipeHairBeardMaskAdapter(detector=lambda _img: _synthetic_landmarks())
    service = VisagismSimulationService(mask_adapter=adapter, verifier=AlwaysPassVerifier())

    result = service.simulate(
        original_photo=original,
        real_reference_photos=refs,
        source_photos=[{"image": original}, *({"image": ref} for ref in refs)],
        preferred_original=original,
        edit_instruction="short textured crop",
    )

    assert result["simulation_status"] == "blocked"
    assert result["reason"] == "invalid_reference_count"
    assert result["card_media"]["simulationApplied"] is False
    assert result["card_media"]["displayImage"] is original


def test_service_ready_path_is_pixel_locked_and_identity_guarded():
    original = _image(60)
    refs = [_image(61), _image(62), _image(63)]
    adapter = MediaPipeHairBeardMaskAdapter(detector=lambda _img: _synthetic_landmarks())
    service = VisagismSimulationService(
        mask_adapter=adapter,
        verifier=AlwaysPassVerifier(),
        renderer=FullFrameRenderer(),
    )

    result = service.simulate(
        original_photo=original,
        real_reference_photos=refs,
        source_photos=[{"image": original}, *({"image": ref} for ref in refs)],
        preferred_original=original,
        edit_instruction="short textured crop",
    )

    assert result["simulation_status"] == "ready"
    assert result["card_media"]["simulationApplied"] is True
    candidate = result["card_media"]["displayImage"]
    mask = adapter.build_hair_beard_mask(original)["mask"] > 0
    original_arr = np.asarray(original)
    candidate_arr = np.asarray(candidate)
    assert np.array_equal(candidate_arr[~mask], original_arr[~mask])
    assert np.any(candidate_arr[mask] != original_arr[mask])


def test_service_blocks_when_reference_identity_gate_fails():
    class OneFailVerifier:
        calls = 0

        def compare(self, candidate, reference):
            self.calls += 1
            return 0.79 if self.calls == 2 else 0.90

    original = _image(60)
    refs = [_image(61), _image(62), _image(63)]
    adapter = MediaPipeHairBeardMaskAdapter(detector=lambda _img: _synthetic_landmarks())
    service = VisagismSimulationService(mask_adapter=adapter, verifier=OneFailVerifier())

    result = service.simulate(
        original_photo=original,
        real_reference_photos=refs,
        source_photos=[{"image": original}, *({"image": ref} for ref in refs)],
        preferred_original=original,
        edit_instruction="short textured crop",
    )

    assert result["simulation_status"] == "blocked"
    assert result["reason"] == "reference_identity_gate_failed"
    assert result["card_media"]["displayImage"] is original
