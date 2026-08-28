from PIL import Image

from app.ai.visagism.adapters.aws_rekognition_identity import (
    AWSRekognitionIdentityVerifier,
)


class FakeRekognition:
    def __init__(self, similarity=92.5, error=False):
        self.similarity = similarity
        self.error = error
        self.calls = 0
        self.last_kwargs = None

    def compare_faces(self, **kwargs):
        self.calls += 1
        self.last_kwargs = kwargs
        if self.error:
            raise RuntimeError("boom")
        return {"FaceMatches": [{"Similarity": self.similarity}]}


def test_same_image_object_shortcuts_to_perfect_identity_without_api_call():
    client = FakeRekognition()
    verifier = AWSRekognitionIdentityVerifier(client=client)
    image = Image.new("RGB", (4, 4))

    assert verifier.compare(image, image) == 1.0
    assert client.calls == 0


def test_rekognition_similarity_is_normalized_to_zero_one():
    client = FakeRekognition(similarity=92.5)
    verifier = AWSRekognitionIdentityVerifier(client=client)

    score = verifier.compare(Image.new("RGB", (4, 4)), Image.new("RGB", (4, 4)))

    assert score == 0.925
    assert client.calls == 1


def test_identity_verifier_fails_closed_on_aws_error():
    verifier = AWSRekognitionIdentityVerifier(client=FakeRekognition(error=True))

    score = verifier.compare(Image.new("RGB", (4, 4)), Image.new("RGB", (4, 4)))

    assert score == 0.0


def test_rekognition_encoding_bounds_large_images_before_upload():
    client = FakeRekognition()
    verifier = AWSRekognitionIdentityVerifier(client=client)

    verifier.compare(Image.new("RGB", (4000, 3000)), Image.new("RGB", (3000, 4000)))

    source_bytes = client.last_kwargs["SourceImage"]["Bytes"]
    target_bytes = client.last_kwargs["TargetImage"]["Bytes"]
    for raw in (source_bytes, target_bytes):
        from io import BytesIO

        with Image.open(BytesIO(raw)) as encoded:
            assert max(encoded.size) <= verifier.max_encode_side
