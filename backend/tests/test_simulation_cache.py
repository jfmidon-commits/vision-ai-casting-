from app.ai.visagism.simulation_cache import (
    CACHE_FIELD,
    cache_key,
    find_ready,
    object_key,
    prompt_fingerprint,
    ready_for_source,
    with_ready_entry,
)


def _prompt_hash(text: str = "prompt-v1") -> str:
    return prompt_fingerprint(text, denoising=0.30, identity_weight=0.90)


def test_cache_key_is_stable_and_prompt_sensitive():
    prompt_hash = _prompt_hash()
    first = cache_key(
        haircut_name="Quiff texturizado",
        source_photo_id="photo-1",
        provider="fal",
        model="model-v1",
        prompt_hash=prompt_hash,
    )
    second = cache_key(
        haircut_name="Quiff texturizado",
        source_photo_id="photo-1",
        provider="fal",
        model="model-v1",
        prompt_hash=prompt_hash,
    )
    other_prompt = cache_key(
        haircut_name="Quiff texturizado",
        source_photo_id="photo-1",
        provider="fal",
        model="model-v1",
        prompt_hash=_prompt_hash("prompt-v2"),
    )
    assert first == second
    assert first != other_prompt


def test_ready_entry_round_trips_without_image_bytes_in_jsonb():
    key = "abc123"
    prompt_hash = _prompt_hash()
    visagism = with_ready_entry(
        {"recommended_hairstyles": ["Quiff texturizado"]},
        key=key,
        haircut_name="Quiff texturizado",
        source_photo_id="photo-1",
        provider="fal",
        model="model-v1",
        prompt_hash=prompt_hash,
        denoising=0.30,
        identity_weight=0.90,
        stored_object_key="visagism-simulations/t/a/abc123.png",
        identity_score_min=0.91,
        mask_kind="hair-v2",
    )
    cached = find_ready(
        visagism,
        haircut_name="Quiff texturizado",
        source_photo_id="photo-1",
        provider="fal",
        model="model-v1",
        prompt_hash=prompt_hash,
    )
    assert cached is not None
    assert cached["object_key"].endswith("abc123.png")
    assert cached["prompt_hash"] == prompt_hash
    assert cached["identity_score_min"] == 0.91
    assert "image" not in cached
    assert "base64" not in str(visagism[CACHE_FIELD]).lower()


def test_cache_rejects_different_prompt_fingerprint():
    stored_hash = _prompt_hash("old")
    visagism = with_ready_entry(
        {},
        key="one",
        haircut_name="Quiff",
        source_photo_id="photo-1",
        provider="fal",
        model="v1",
        prompt_hash=stored_hash,
        denoising=0.30,
        identity_weight=0.90,
        stored_object_key="one.png",
        identity_score_min=0.9,
    )
    assert (
        find_ready(
            visagism,
            haircut_name="Quiff",
            source_photo_id="photo-1",
            provider="fal",
            model="v1",
            prompt_hash=_prompt_hash("new"),
        )
        is None
    )


def test_ready_for_source_returns_only_matching_ready_simulations():
    prompt_hash = _prompt_hash()
    visagism = with_ready_entry(
        {},
        key="one",
        haircut_name="Quiff",
        source_photo_id="photo-1",
        provider="fal",
        model="v1",
        prompt_hash=prompt_hash,
        denoising=0.30,
        identity_weight=0.90,
        stored_object_key="one.png",
        identity_score_min=0.9,
    )
    visagism = with_ready_entry(
        visagism,
        key="two",
        haircut_name="Side Part",
        source_photo_id="photo-2",
        provider="fal",
        model="v1",
        prompt_hash=prompt_hash,
        denoising=0.30,
        identity_weight=0.90,
        stored_object_key="two.png",
        identity_score_min=0.91,
    )
    items = list(ready_for_source(visagism, source_photo_id="photo-1"))
    assert len(items) == 1
    assert items[0]["haircut_name"] == "Quiff"


def test_s3_object_key_is_tenant_and_analysis_scoped():
    key = object_key(tenant_id="tenant-1", analysis_id="analysis-1", key="hash")
    assert key == "visagism-simulations/tenant-1/analysis-1/hash.png"
