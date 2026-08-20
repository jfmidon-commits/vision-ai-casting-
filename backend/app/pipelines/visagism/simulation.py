"""Provider-neutral interface for optional hairstyle simulation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Mapping, Optional


class HairSimulationProvider(ABC):
    """Contract for optional external or local hairstyle simulation providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Stable provider identifier."""
        raise NotImplementedError

    @abstractmethod
    def simulate(
        self,
        reference_image_path: str,
        recommendation: Mapping[str, Any],
        output_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create or request a simulation without changing pipeline evidence."""
        raise NotImplementedError


class NullHairSimulationProvider(HairSimulationProvider):
    """Default provider that explicitly reports simulation as unavailable."""

    @property
    def name(self) -> str:
        return "none"

    def simulate(
        self,
        reference_image_path: str,
        recommendation: Mapping[str, Any],
        output_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        return {
            "available": False,
            "provider": self.name,
            "reference_image": reference_image_path,
            "output_path": None,
            "reason": "no_hair_simulation_provider_configured",
            "identity_preservation_validated": False,
        }
