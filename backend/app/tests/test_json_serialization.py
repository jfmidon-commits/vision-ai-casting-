import json

import numpy as np
import pytest

from app.utils.json_serialization import json_dumps


def test_serializes_numpy_bool_nested_in_analysis_payload():
    payload = {
        "photogenic": {
            "overall_score": 0.82,
            "dimensions": {
                "symmetry": {
                    "measured": np.bool_(True),
                }
            },
        }
    }

    encoded = json_dumps(payload)
    decoded = json.loads(encoded)

    assert decoded["photogenic"]["dimensions"]["symmetry"]["measured"] is True


def test_serializes_numpy_scalar_types():
    payload = {
        "bool": np.bool_(False),
        "int": np.int64(7),
        "float": np.float32(0.75),
    }

    decoded = json.loads(json_dumps(payload))

    assert decoded["bool"] is False
    assert decoded["int"] == 7
    assert decoded["float"] == pytest.approx(0.75)


def test_serializes_numpy_array():
    payload = {"scores": np.array([1, 2, 3], dtype=np.int64)}

    decoded = json.loads(json_dumps(payload))

    assert decoded["scores"] == [1, 2, 3]


def test_serializes_nested_numpy_values_inside_array():
    payload = {
        "matrix": np.array([[True, False], [False, True]], dtype=np.bool_),
    }

    decoded = json.loads(json_dumps(payload))

    assert decoded["matrix"] == [[True, False], [False, True]]


def test_unsupported_object_still_raises_type_error():
    class Unsupported:
        pass

    with pytest.raises(TypeError, match="not JSON serializable"):
        json_dumps({"value": Unsupported()})
