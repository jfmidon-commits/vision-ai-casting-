"""Live smoke test for Vision visagism image editing via Cloudflare Workers AI.

The image simulator module is loaded directly from its file so this focused
smoke test does not import the full visagism package (MediaPipe/OpenCV, etc.).
"""

from __future__ import annotations

import asyncio
import base64
import importlib.util
import io
import os
import sys
from pathlib import Path

from PIL import Image


BACKEND_ROOT = Path(__file__).resolve().parents[1]
SIMULATOR_PATH = BACKEND_ROOT / "app" / "ai" / "visagism" / "image_simulator.py"
FIXTURE = Path("tests/fixtures/visagism/dataset_001/01_frontal_neutra_close.jpg")
OUTPUT = Path("benchmark_results/live/visagism_visual_smoke.png")


def _load_simulator_class():
    """Load only image_simulator.py without executing visagism/__init__.py."""
    spec = importlib.util.spec_from_file_location(
        "vision_visagism_image_simulator", SIMULATOR_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Nao foi possivel carregar {SIMULATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.VisagismImageSimulator


RECOMMENDATION = {
    "display_name": "Topo texturizado com volume e taper suave",
    "barber_instructions": (
        "Manter 6-9 cm no topo, com mais comprimento na regiao frontal; "
        "texturizar com tesoura e fazer taper baixo/suave nas laterais e nuca, "
        "sem fade alto e sem criar volume junto a mandibula."
    ),
    "styling": "Secador elevando a raiz e acabamento fosco natural.",
    "volume_distribution": "mais volume no topo e frontal",
    "side_treatment": "taper baixo e suave",
    "forehead_exposure": "frente elevada ou parcialmente aberta",
}


async def main() -> None:
    if not os.environ.get("CLOUDFLARE_API_TOKEN"):
        raise SystemExit("LIVE_SMOKE_BLOCKED: CLOUDFLARE_API_TOKEN nao configurado")
    if not os.environ.get("CLOUDFLARE_ACCOUNT_ID"):
        raise SystemExit("LIVE_SMOKE_BLOCKED: CLOUDFLARE_ACCOUNT_ID nao configurado")
    if not FIXTURE.exists():
        raise SystemExit(f"LIVE_SMOKE_BLOCKED: fixture nao encontrada: {FIXTURE}")

    VisagismImageSimulator = _load_simulator_class()
    simulator = VisagismImageSimulator()
    result = await simulator.generate(
        source_photo_url=str(FIXTURE),
        recommendation=RECOMMENDATION,
        face_shape="triangular",
    )

    if result.status != "completed" or not result.image_data_url:
        raise SystemExit(
            "LIVE_SMOKE_FAILED: "
            f"status={result.status}; error={result.error or 'sem detalhe'}"
        )
    if result.provider != "cloudflare":
        raise SystemExit(
            f"LIVE_SMOKE_FAILED: esperado provider=cloudflare; recebido={result.provider}"
        )

    prefix = "data:image/png;base64,"
    if not result.image_data_url.startswith(prefix):
        raise SystemExit("LIVE_SMOKE_FAILED: resposta nao retornou PNG base64 esperado")

    image_bytes = base64.b64decode(result.image_data_url[len(prefix) :])
    image = Image.open(io.BytesIO(image_bytes))
    image.verify()

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_bytes(image_bytes)

    print(
        "LIVE_SMOKE_SUCCESS: Cloudflare visual simulation generated and decoded; "
        f"provider={result.provider}; model={result.model}; bytes={len(image_bytes)}"
    )


if __name__ == "__main__":
    asyncio.run(main())
