import numpy as np
from PIL import Image

from app.ai.visagism.adapters.mediapipe_hair_mask import MediaPipeHairBeardMaskAdapter


def _landmarks():
    points = [(0.5, 0.55)] * 478
    adapter = MediaPipeHairBeardMaskAdapter()
    rectangle = [(0.30, 0.35), (0.70, 0.35), (0.70, 0.75), (0.30, 0.75)]
    for index, landmark_index in enumerate(adapter.FACE_OVAL):
        points[landmark_index] = rectangle[index % len(rectangle)]
    return points


def test_hair_mask_is_above_face_and_never_reaches_beard_region():
    image = np.zeros((100, 100, 3), dtype=np.uint8)
    adapter = MediaPipeHairBeardMaskAdapter(
        detector=lambda _: _landmarks(),
        person_segmenter=lambda _: np.ones((100, 100), dtype=np.float32),
    )

    result = adapter.build_hair_mask(image)

    assert result["valid"] is True
    assert result["beard_enabled"] is False
    assert result["background_locked"] is True
    mask = result["mask"]
    # Face oval begins around y=35, so jaw/beard pixels below it stay locked.
    assert np.all(mask[35:, :] == 0)
    assert np.any(mask[:35, :] > 0)


def test_hair_mask_intersects_person_segmentation_to_lock_background():
    image = np.zeros((100, 100, 3), dtype=np.uint8)
    person = np.zeros((100, 100), dtype=np.float32)
    person[:, 35:65] = 1.0
    adapter = MediaPipeHairBeardMaskAdapter(
        detector=lambda _: _landmarks(),
        person_segmenter=lambda _: person,
    )

    result = adapter.build_hair_mask(image)

    assert result["valid"] is True
    mask = result["mask"]
    assert np.all(mask[:, :34] == 0)
    assert np.all(mask[:, 66:] == 0)
    assert np.any(mask[:, 36:64] > 0)


def test_hair_mask_fails_closed_when_person_segmentation_is_missing():
    image = np.zeros((100, 100, 3), dtype=np.uint8)
    adapter = MediaPipeHairBeardMaskAdapter(
        detector=lambda _: _landmarks(),
        person_segmenter=lambda _: None,
    )

    result = adapter.build_hair_mask(image)

    assert result["valid"] is False
    assert result["reason"] == "person_segmentation_failed"
    assert np.count_nonzero(result["mask"]) == 0


def test_legacy_hair_beard_method_is_hair_only_alias():
    image = np.zeros((100, 100, 3), dtype=np.uint8)
    adapter = MediaPipeHairBeardMaskAdapter(
        detector=lambda _: _landmarks(),
        person_segmenter=lambda _: np.ones((100, 100), dtype=np.float32),
    )

    result = adapter.build_hair_beard_mask(image)

    assert result["valid"] is True
    assert result["beard_enabled"] is False
    assert result["mask_kind"] == "person_intersection_hair_roi_v2"


def test_media_inference_resize_caps_longest_side_and_preserves_aspect_ratio():
    image = np.zeros((3000, 4000, 3), dtype=np.uint8)
    adapter = MediaPipeHairBeardMaskAdapter(inference_max_side=768)

    resized = adapter._resize_for_inference(image)

    assert resized.shape == (576, 768, 3)


def test_media_inference_resize_keeps_small_images_unchanged():
    image = np.zeros((480, 640, 3), dtype=np.uint8)
    adapter = MediaPipeHairBeardMaskAdapter(inference_max_side=768)

    resized = adapter._resize_for_inference(image)

    assert resized is image


def test_full_mask_pipeline_runs_bounded_and_restores_source_mask_size():
    seen = {}

    def detector(image):
        seen["detector_shape"] = image.shape
        return _landmarks()

    def segmenter(image):
        seen["segmenter_shape"] = image.shape
        return np.ones(image.shape[:2], dtype=np.float32)

    source = Image.new("RGB", (1600, 1200), "white")
    adapter = MediaPipeHairBeardMaskAdapter(
        inference_max_side=400,
        detector=detector,
        person_segmenter=segmenter,
    )

    result = adapter.build_hair_mask(source)

    assert result["valid"] is True
    assert seen["detector_shape"] == (300, 400, 3)
    assert seen["segmenter_shape"] == (300, 400, 3)
    assert result["mask"].shape == (1200, 1600)
