"""
backend/app/ai/image_triage/__init__.py

Modulo de triagem inteligente de imagens para visagismo.

Seleciona automaticamente as melhores imagens de um conjunto,
pontuando qualidade e classificando por angulo facial util ao
protocolo de visagismo do Vision AI Casting.

Pode ser usado como:
- Script standalone local (CLI)
- Modulo integrado no pipeline do Vision AI Casting
- API endpoint para triagem em lote

Principio: NUNCA modifica os originais. Sempre trabalha em copia.
"""

from app.ai.image_triage.schemas import (
    TriageInput, TriageResult, ImageCandidate,
    FaceAngle, QualityScore, TriageConfig,
)
from app.ai.image_triage.engine import ImageTriageEngine
from app.ai.image_triage.cli import main as cli_main

__all__ = [
    "TriageInput",
    "TriageResult", 
    "ImageCandidate",
    "FaceAngle",
    "QualityScore",
    "TriageConfig",
    "ImageTriageEngine",
    "cli_main",
]
