from app.pipelines.visagism.measurements import FacialMeasurementEngine


def _landmarks():
    points = [{"x": 0.5, "y": 0.5, "z": 0.0} for _ in range(478)]
    points[1] = {"x": 0.5, "y": 0.5, "z": 0.0}
    points[10] = {"x": 0.5, "y": 0.2, "z": 0.0}
    points[152] = {"x": 0.5, "y": 0.8, "z": 0.0}
    points[234] = {"x": 0.2, "y": 0.5, "z": 0.0}
    points[454] = {"x": 0.8, "y": 0.5, "z": 0.0}
    points[33] = {"x": 0.35, "y": 0.4, "z": 0.0}
    points[263] = {"x": 0.65, "y": 0.4, "z": 0.0}
    points[133] = {"x": 0.42, "y": 0.4, "z": 0.0}
    points[362] = {"x": 0.58, "y": 0.4, "z": 0.0}
    points[58] = {"x": 0.28, "y": 0.68, "z": 0.0}
    points[288] = {"x": 0.72, "y": 0.68, "z": 0.0}
    points[61] = {"x": 0.4, "y": 0.62, "z": 0.0}
    points[291] = {"x": 0.6, "y": 0.62, "z": 0.0}
    points[105] = {"x": 0.42, "y": 0.34, "z": 0.0}
    points[334] = {"x": 0.58, "y": 0.34, "z": 0.0}
    return points


def test_measurements_are_traceable_and_normalized():
    result = FacialMeasurementEngine.from_landmarks(_landmarks())

    assert result["face_detected"] is True
    assert result["evidence_source"] == "MediaPipe FaceLandmarker"
    assert result["measurements"]["face_width"]["unit"] == "normalized_image_ratio"
    assert result["measurements"]["face_height_to_width"]["unit"] == "ratio"
    assert result["measurements"]["face_width"]["status"] == "observed"
    assert "measurements_are_normalized_not_physical" in result["limitations"]


def test_measurements_reject_insufficient_landmarks():
    result = FacialMeasurementEngine.from_landmarks([{"x": 0.5, "y": 0.5, "z": 0.0}])

    assert result["face_detected"] is False
    assert result["measurements"] == {}
    assert "insufficient_facemesh_landmarks" in result["limitations"]
