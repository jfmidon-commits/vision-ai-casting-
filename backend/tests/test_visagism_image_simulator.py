import pytest

from app.ai.visagism.image_simulator import VisagismImageSimulator
from app.config import settings


@pytest.mark.asyncio
async def test_visual_simulation_returns_data_url(monkeypatch):
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "test-key")
    simulator = VisagismImageSimulator()

    async def fake_load_source_image(_source):
        return b"image-bytes", "portrait.jpg", "image/jpeg"

    async def fake_request_edit(**kwargs):
        assert kwargs["image_bytes"] == b"image-bytes"
        assert "Topo texturizado" in kwargs["prompt"]
        assert "Preserve com alta fidelidade" in kwargs["prompt"]
        return {"data": [{"b64_json": "aW1hZ2U="}]}

    monkeypatch.setattr(simulator, "_load_source_image", fake_load_source_image)
    monkeypatch.setattr(simulator, "_request_edit", fake_request_edit)

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
    assert result.image_data_url == "data:image/png;base64,aW1hZ2U="
    assert result.error is None


@pytest.mark.asyncio
async def test_visual_simulation_requires_api_key(monkeypatch):
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "")
    simulator = VisagismImageSimulator()

    result = await simulator.generate(
        source_photo_url="https://example.com/portrait.jpg",
        recommendation={"display_name": "Topo texturizado"},
        face_shape="triangular",
    )

    assert result.status == "unavailable"
    assert result.image_data_url is None
    assert "OPENAI_API_KEY" in result.error


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
