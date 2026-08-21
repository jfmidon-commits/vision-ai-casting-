"""Artifact manifest for reproducible visagism runs."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, Mapping


class VisagismArtifactManifest:
    """Describe generated outputs with hashes for traceability."""

    SCHEMA_VERSION = "1.0"

    def build(self, result: Mapping[str, Any]) -> Dict[str, Any]:
        artifacts: Dict[str, Any] = {}
        card = result.get("card")
        if isinstance(card, Mapping):
            path = card.get("path")
            if isinstance(path, str):
                artifacts["card"] = self._describe_file(path, "image/png")

        simulation = result.get("simulation")
        if isinstance(simulation, Mapping) and simulation.get("available") is True:
            path = simulation.get("output_path") or simulation.get("path")
            if isinstance(path, str):
                artifacts["simulation"] = self._describe_file(path, "image")

        return {
            "schema_version": self.SCHEMA_VERSION,
            "pipeline": "RealVisagismPipeline",
            "artifacts": artifacts,
        }

    def write_json(self, result: Mapping[str, Any], output_path: str) -> Dict[str, Any]:
        manifest = self.build(result)
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return {"path": str(target), "manifest": manifest}

    @staticmethod
    def _describe_file(path: str, media_type: str) -> Dict[str, Any]:
        if not os.path.isfile(path):
            return {"path": path, "exists": False, "media_type": media_type}
        digest = hashlib.sha256()
        with open(path, "rb") as file_obj:
            for chunk in iter(lambda: file_obj.read(65536), b""):
                digest.update(chunk)
        return {
            "path": path,
            "exists": True,
            "media_type": media_type,
            "size_bytes": os.path.getsize(path),
            "sha256": digest.hexdigest(),
        }
