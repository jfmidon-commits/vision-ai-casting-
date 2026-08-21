from pathlib import Path

from PIL import Image

from app.pipelines.visagism import BarberCardGenerator


def _recommendation():
    return {
        "name": "Classic Scissor Taper",
        "compatibility_score": 0.91,
        "top_cm": (5.0, 7.0),
        "sides_mm": (12, 25),
        "fade": "low taper",
        "connection": "soft scissor connection",
        "direction": "natural side",
        "finish": "matte",
        "maintenance": "3-5 weeks",
        "avoid": "high fade",
        "reasons": ["compatible with oval face geometry"],
        "risks": ["keep temples conservative"],
    }


def test_barber_card_is_real_1080x1920_png(tmp_path: Path):
    reference = tmp_path / "reference.jpg"
    output = tmp_path / "card.png"
    Image.new("RGB", (600, 800), "white").save(reference)

    result = BarberCardGenerator().generate(
        str(reference),
        _recommendation(),
        str(output),
    )

    assert output.exists()
    with Image.open(output) as image:
        assert image.size == (1080, 1920)
        assert image.format == "PNG"
    assert result["synthetic_simulation_used"] is False
    assert result["reference_image"] == str(reference)
