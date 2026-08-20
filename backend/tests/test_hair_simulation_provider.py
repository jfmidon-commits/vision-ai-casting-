from app.pipelines.visagism import NullHairSimulationProvider


def test_null_provider_never_fabricates_simulation():
    provider = NullHairSimulationProvider()
    result = provider.simulate(
        "reference.jpg",
        {"name": "Classic Scissor Taper"},
        "simulation.png",
    )

    assert result["available"] is False
    assert result["provider"] == "none"
    assert result["output_path"] is None
    assert result["identity_preservation_validated"] is False
    assert result["reason"] == "no_hair_simulation_provider_configured"
