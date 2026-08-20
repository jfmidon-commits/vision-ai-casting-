import json

from app.pipelines.visagism.artifacts import VisagismArtifactManifest


def test_artifact_manifest_hashes_generated_card(tmp_path):
    card = tmp_path / "card.png"
    card.write_bytes(b"vision-card-test")
    output = tmp_path / "manifest.json"

    writer = VisagismArtifactManifest()
    written = writer.write_json(
        {"card": {"path": str(card)}, "simulation": {"available": False}},
        str(output),
    )

    assert output.exists()
    payload = json.loads(output.read_text(encoding="utf-8"))
    described = payload["artifacts"]["card"]
    assert described["exists"] is True
    assert described["size_bytes"] == len(b"vision-card-test")
    assert len(described["sha256"]) == 64
    assert written["manifest"] == payload
