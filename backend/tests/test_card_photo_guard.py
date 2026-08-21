import pytest

from app.ai.visagism.card_photo_guard import CardPhotoGuard, CardPhotoGuardError


def test_card_always_contains_real_person_photo():
    guard = CardPhotoGuard()
    photos = [{"url": "real-front.jpg"}, {"url": "real-side.jpg"}]

    media = guard.build_card_media(photos=photos)

    assert media["personPhoto"] == "real-front.jpg"
    assert media["displayImage"] == "real-front.jpg"
    assert media["realPhotoVerified"] is True
    assert media["simulationApplied"] is False


def test_card_refuses_to_exist_without_real_photo():
    guard = CardPhotoGuard()

    with pytest.raises(CardPhotoGuardError, match="card_requires_real_person_photo"):
        guard.build_card_media(photos=[{"foo": "bar"}])


def test_preferred_person_photo_must_come_from_analysis_inputs():
    guard = CardPhotoGuard()
    photos = [{"url": "real-front.jpg"}]

    with pytest.raises(CardPhotoGuardError, match="preferred_photo_not_in_analysis_inputs"):
        guard.build_card_media(photos=photos, preferred_original="other-person.jpg")


def test_unverified_generated_portrait_can_never_replace_person_photo():
    guard = CardPhotoGuard()
    photos = [{"url": "real-front.jpg"}]
    fake_publication = {
        "image": "generated-similar-face.jpg",
        "simulationApplied": True,
        "identityVerified": False,
        "layers": {"base": "real-front.jpg", "overlay": "generated-similar-face.jpg"},
    }

    media = guard.build_card_media(photos=photos, publication=fake_publication)

    assert media["personPhoto"] == "real-front.jpg"
    assert media["displayImage"] == "real-front.jpg"
    assert media["simulationApplied"] is False
    assert media["fallbackUsed"] is True


def test_even_validated_simulation_keeps_real_person_photo_on_card():
    guard = CardPhotoGuard()
    photos = [{"url": "real-front.jpg"}, {"url": "real-side.jpg"}]
    publication = {
        "image": "hair-beard-overlay-result.jpg",
        "simulationApplied": True,
        "identityVerified": True,
        "layers": {"base": "real-front.jpg", "overlay": "hair-beard-overlay-result.jpg"},
    }

    media = guard.build_card_media(photos=photos, publication=publication)

    assert media["personPhoto"] == "real-front.jpg"
    assert media["displayImage"] == "hair-beard-overlay-result.jpg"
    assert media["displayMode"] == "validated_hair_beard_overlay"
    assert media["simulationApplied"] is True
    assert media["identityVerified"] is True


def test_simulation_is_blocked_if_its_base_is_not_the_selected_real_photo():
    guard = CardPhotoGuard()
    photos = [{"url": "real-front.jpg"}, {"url": "real-side.jpg"}]
    publication = {
        "image": "overlay.jpg",
        "simulationApplied": True,
        "identityVerified": True,
        "layers": {"base": "real-side.jpg", "overlay": "overlay.jpg"},
    }

    media = guard.build_card_media(
        photos=photos,
        preferred_original="real-front.jpg",
        publication=publication,
    )

    assert media["personPhoto"] == "real-front.jpg"
    assert media["displayImage"] == "real-front.jpg"
    assert media["simulationApplied"] is False
    assert media["fallbackUsed"] is True


def test_arbitrary_generated_image_is_never_registered_as_real_reference():
    guard = CardPhotoGuard()
    photos = [{"url": "real-front.jpg"}, {"path": "/tmp/real-side.jpg"}]

    media = guard.build_card_media(photos=photos)

    assert media["realPhotoRefs"] == ["real-front.jpg", "/tmp/real-side.jpg"]
    assert "generated.jpg" not in media["realPhotoRefs"]
