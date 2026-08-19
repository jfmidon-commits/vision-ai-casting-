import pytest

from app.ai.visagism.image_simulator import VisagismImageSimulator
from app.config import settings


@pytest.mark.asyncio
async def test_visual_simulation_prefers_cloudflare(monkeypatch):
    monkeypatch.setattr(settings, "CLOUDFLARE_API_TOKEN", "cf-token")
    monkeypatch.setattr(settings, "CLOUDFLARE_ACCOUNT_ID", "cf-account")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "openai-key")
    simulator = VisagismImageSimulator()

    async def fake_load_source_image(_source):
        return b"image-bytes", "portrait.jpg", "image/jpeg"

    async def fake_request_cloudflare_edit(**kwargs):
        assert kwargs["image_bytes"] == b"cloudflare-image"
        assert "Topo texturizado" in kwargs["prompt"]
        assert "Preserve com alta fidelidade" in kwargs["prompt"]
        return {"success": True, "result": {"image": "aW1hZ2U="}}

    async def fail_openai(**_kwargs):
        raise AssertionError("OpenAI fallback nao deveria ser chamado")

    monkeypatch.setattr(simulator, "_load_source_image", fake_load_source_image)
    monkeypatch.setattr(simulator, "_prepare_cloudflare_input", lambda _value: b"cloudflare-image")
    monkeypatch.setattr(simulator, "_request_cloudflare_edit", fake_request_cloudflare_edit)
    monkeypatch.setattr(simulator, "_request_openai_edit", fail_openai)

    result = await simulator.generate(
        source_photo_url="https://example.com/portrait.jpg",
        recommendation={
            "display_name": "Topo texturizado com volume e taper suave",
            "barber_instructions": "Manter 6-9 cm no topo e taper baixo suave.",
            "styling": "Finalizacao fosca e natural.",
        },
        face_shape="triangular",
    )

    assert result.status == "completed"
    assert result.provider == "cloudflare"
    assert result.model == settings.CLOUDFLARE_IMAGE_MODEL
    assert result.image_data_url == "data:image/png;base64,aW1hZ2U="
    assert result.error is None


@pytest.mark.asyncio
async def test_visual_simulation_uses_openai_fallback(monkeypatch):
    monkeypatch.setattr(settings, "CLOUDFLARE_API_TOKEN", "cf-token")
    monkeypatch.setattr(settings, "CLOUDFLARE_ACCOUNT_ID", "cf-account")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "openai-key")
    simulator = VisagismImageSimulator()

    async def fake_load_source_image(_source):
        return b"image-bytes", "portrait.jpg", "image/jpeg"

    async def fail_cloudflare(**_kwargs):
        raise RuntimeError("temporariamente indisponivel")

    async def fake_openai(**_kwargs):
        return {"data": [{"b64_json": "b3BlbmFp"}]}

    monkeypatch.setattr(simulator, "_load_source_image", fake_load_source_image)
    monkeypatch.setattr(simulator, "_prepare_cloudflare_input", lambda _value: b"cloudflare-image")
    monkeypatch.setattr(simulator, "_request_cloudflare_edit", fail_cloudflare)
    monkeypatch.setattr(simulator, "_request_openai_edit", fake_openai)

    result = await simulator.generate(
        source_photo_url="https://example.com/portrait.jpg",
        recommendation={"display_name": "Topo texturizado"},
        face_shape="triangular",
    )

    assert result.status == "completed"
    assert result.provider == "openai"
    assert result.image_data_url == "data:image/png;base64,b3BlbmFp"


@pytest.mark.asyncio
async def test_visual_simulation_requires_provider_credentials(monkeypatch):
    monkeypatch.setattr(settings, "CLOUDFLARE_API_TOKEN", "")
    monkeypatch.setattr(settings, "CLOUDFLARE_ACCOUNT_ID", "")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "")
    simulator = VisagismImageSimulator()

    result = await simulator.generate(
        source_photo_url="https://example.com/portrait.jpg",
        recommendation={"display_name": "Topo texturizado"},
        face_shape="triangular",
    )

    assert result.status == "unavailable"
    assert result.image_data_url is None
    assert "Nenhum provedor visual" in result.error


def test_cloudflare_response_extraction():
    payload = {"success": True, "result": {"image": "Zm9v"}}
    assert VisagismImageSimulator._extract_cloudflare_image_base64(payload) == "Zm9v"


def test_prompt_preserves_identity_and_accepts_presenter_string():
    prompt = VisagismImageSimulator._build_prompt(
        {
            "display_name": "Topo texturizado com volume e taper suave",
            "barber_instructions": "Manter 6-9 cm no topo; taper baixo e suave.",
            "styling": "Secador e pasta fosca leve.",
        },
        "triangular",
    )

    assert "Edite SOMENTE o cabelo" in prompt
    assert "Nao embeleze nem altere tracos faciais" in prompt
    assert "6-9 cm" in prompt
    assert "triangular" in prompt
