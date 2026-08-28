from PIL import Image

from app.ai.visagism.adapters.aws_rekognition_identity import (
    AWSRekognitionIdentityVerifier,
)


class FakeRekognitionClient:
    def __init__(self, response=None, error=None):
        self.response = response or {"FaceMatches": []}
        self.error = error
        self.calls = []

    def compare_faces(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.response


def _image(value=80):
    return Image.new("RGB", (120, 160), (value, value, value))


def test_compare_disables_provider_quality_filter_and_normalizes_similarity():
    client = FakeRekognitionClient(
        {"FaceMatches": [{"Similarity": 91.5}, {"Similarity": 84.0}]}
    )
    verifier = AWSRekognitionIdentityVerifier(client=client)

    score = verifier.compare(_image(80), _image(81))

    assert score == 0.915
    assert len(client.calls) == 1
    call = client.calls[0]
    assert call["QualityFilter"] == "NONE"
    assert call["SimilarityThreshold"] == 0
    assert call["SourceImage"]["Bytes"]
    assert call["TargetImage"]["Bytes"]


def test_compare_without_face_match_fails_closed():
    verifier = AWSRekognitionIdentityVerifier(client=FakeRekognitionClient())

    assert verifier.compare(_image(80), _image(81)) == 0.0


def test_compare_provider_error_fails_closed():
    client = FakeRekognitionClient(error=RuntimeError("rekognition unavailable"))
    verifier = AWSRekognitionIdentityVerifier(client=client)

    assert verifier.compare(_image(80), _image(81)) == 0.0


def test_compare_same_object_short_circuits_without_provider_call():
    client = FakeRekognitionClient()
    verifier = AWSRekognitionIdentityVerifier(client=client)
    image = _image(80)

    assert verifier.compare(image, image) == 1.0
    assert client.calls == []
