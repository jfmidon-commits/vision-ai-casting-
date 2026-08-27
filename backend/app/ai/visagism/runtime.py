"""Runtime selection for visagism simulation providers.

All selections are explicit and fail closed. Missing credentials never fall
back to an unconfigured or heavyweight verifier silently.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from app.config import settings

from .adapters.aws_rekognition_identity import AWSRekognitionIdentityVerifier
from .providers.fal_renderer import FalOverlayRenderer


@dataclass(frozen=True)
class SimulationRuntime:
    renderer: Optional[Any]
    verifier: Optional[Any]
    provider: str
    model: str
    provider_configured: bool
    identity_provider: str
    identity_configured: bool


def create_simulation_runtime() -> SimulationRuntime:
    provider = settings.VISAGISM_SIMULATION_PROVIDER.strip().lower()
    model = settings.VISAGISM_SIMULATION_MODEL.strip()
    renderer: Optional[Any] = None

    if provider == "fal" and settings.FAL_KEY.strip() and model:
        renderer = FalOverlayRenderer(
            api_key=settings.FAL_KEY,
            model=model,
            timeout_seconds=settings.VISAGISM_SIMULATION_TIMEOUT_SECONDS,
        )

    identity_provider = settings.VISAGISM_IDENTITY_PROVIDER.strip().lower()
    verifier: Optional[Any] = None
    if (
        identity_provider == "aws_rekognition"
        and settings.AWS_ACCESS_KEY_ID.strip()
        and settings.AWS_SECRET_ACCESS_KEY.strip()
    ):
        verifier = AWSRekognitionIdentityVerifier()

    return SimulationRuntime(
        renderer=renderer,
        verifier=verifier,
        provider=provider or "disabled",
        model=model,
        provider_configured=renderer is not None,
        identity_provider=identity_provider or "disabled",
        identity_configured=verifier is not None,
    )
