"""Live smoke test for Vision visagism image editing.

This script intentionally performs one real OpenAI image edit. It must only run
when OPENAI_API_KEY is injected by the runtime/CI secret store.
"""

from __future__ import annotations

import asyncio
import base64
import io
import os
from pathlib import Path

from PIL import Image

from app.ai.visagism.image_simulator import VisagismImageSimulator


FIXTURE = Path("tests/fixtures/visagism/dataset_001/01_frontal_neutra_close.jpg")
OUTPUT = Path("benchmark_results/live/visagism_visual_smoke.png")

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
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("LIVE_SMOKE_BLOCKED: OPENAI_API_KEY nao configurada no runtime")

    if not FIXTURE.exists():
        raise SystemExit(f"LIVE_SMOKE_BLOCKED: fixture nao encontrada: {FIXTURE}")

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

    prefix = "data:image/png;base64,"
    if not result.image_data_url.startswith(prefix):
        raise SystemExit("LIVE_SMOKE_FAILED: resposta nao retornou PNG base64 esperado")

    image_bytes = base64.b64decode(result.image_data_url[len(prefix) :])
    image = Image.open(io.BytesIO(image_bytes))
    image.verify()

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_bytes(image_bytes)

    print(
        "LIVE_SMOKE_SUCCESS: visual simulation generated and decoded; "
        f"model={result.model}; bytes={len(image_bytes)}"
    )


if __name__ == "__main__":
    asyncio.run(main())
