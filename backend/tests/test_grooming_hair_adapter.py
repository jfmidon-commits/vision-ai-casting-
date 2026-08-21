import cv2
import numpy as np

from app.pipelines.visagism.grooming_hair_adapter import GroomingHairEvidenceAdapter


class FakeCascade:
    def detectMultiScale(self, *args, **kwargs):
        return np.array([[5, 5, 120, 120]])


class FakeHairMetrics:
    pass


class FakeGroomingAnalyzer:
    def __init__(self):
        self._face_cascade = FakeCascade()
        self.hair_called = False
        self.beard_called = False

    def _get_mediapipe_landmarks(self, img):
        return [{"x": 0.5, "y": 0.5, "px_x": 50, "px_y": 50}] * 468

    def _analyze_hair(self, img, gray, landmarks, x, y, w, h):
        self.hair_called = True
        return FakeHairMetrics()

    def _hair_to_dict(self, hair):
        return {
            "coverage_score": 0.8,
            "volume_score": 0.6,
            "texture_score": 0.5,
            "shine_score": 0.4,
            "neatness_score": 0.7,
            "overall_score": 0.65,
        }

    def _analyze_beard(self, *args, **kwargs):
        self.beard_called = True
        raise AssertionError("hair-only adapter must never call beard analysis")


def test_adapter_runs_only_real_hair_stage():
    analyzer = FakeGroomingAnalyzer()
    adapter = GroomingHairEvidenceAdapter(analyzer=analyzer)

    image = np.full((160, 160, 3), 200, dtype=np.uint8)
    ok, encoded = cv2.imencode(".jpg", image)
    assert ok

    result = adapter.analyze(encoded.tobytes())

    assert analyzer.hair_called is True
    assert analyzer.beard_called is False
    assert result["scope"] == "hair_only"
    assert result["dimensions"]["hair"]["coverage_score"] == 0.8
    assert result["landmarks_detected"] is True
