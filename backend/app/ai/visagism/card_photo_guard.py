"""Hard guard for visagism card media.

A card always carries at least one REAL source photo. A validated haircut
simulation may be displayed, but can never replace provenance of that source.
"""
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional


class CardPhotoGuardError(ValueError):
    """Raised when a card cannot prove real-photo provenance."""


def _photo_value(photo: Mapping[str, Any]) -> Optional[Any]:
    for key in ("url", "path", "image", "src"):
        value = photo.get(key)
        if value:
            return value
    return None


@dataclass(frozen=True)
class CardPhotoGuard:
    def real_photo_refs(self, photos: Iterable[Mapping[str, Any]]) -> List[Any]:
        refs: List[Any] = []
        for photo in photos:
            ref = _photo_value(photo)
            if ref is not None and ref not in refs:
                refs.append(ref)
        return refs

    def select_person_photo(
        self,
        photos: Iterable[Mapping[str, Any]],
        preferred_original: Optional[Any] = None,
    ) -> Any:
        refs = self.real_photo_refs(photos)
        if not refs:
            raise CardPhotoGuardError("card_requires_real_person_photo")
        if preferred_original is not None:
            if preferred_original not in refs:
                raise CardPhotoGuardError("preferred_photo_not_in_analysis_inputs")
            return preferred_original
        return refs[0]

    def build_card_media(
        self,
        *,
        photos: Iterable[Mapping[str, Any]],
        publication: Optional[Mapping[str, Any]] = None,
        preferred_original: Optional[Any] = None,
    ) -> Dict[str, Any]:
        original = self.select_person_photo(photos, preferred_original)
        refs = self.real_photo_refs(photos)

        media: Dict[str, Any] = {
            "personPhoto": original,
            "displayImage": original,
            "displayMode": "original",
            "realPhotoRequired": True,
            "realPhotoVerified": True,
            "realPhotoRefs": refs,
            "simulationApplied": False,
            "identityVerified": False,
            "fallbackUsed": publication is not None,
        }

        if not publication:
            return media

        layers = publication.get("layers") or {}
        base = layers.get("base")
        candidate = publication.get("image")
        simulation_ok = bool(
            publication.get("simulationApplied") is True
            and publication.get("identityVerified") is True
            and publication.get("simulationBlocked") is not True
            and publication.get("mode") == "hair_overlay"
            and candidate is not None
            and base == original
            and base in refs
        )

        if simulation_ok:
            media.update(
                {
                    "displayImage": candidate,
                    "displayMode": "validated_hair_overlay",
                    "simulationApplied": True,
                    "identityVerified": True,
                    "fallbackUsed": False,
                }
            )
        else:
            media.update(
                {
                    "displayImage": original,
                    "displayMode": "original_plus_spec",
                    "simulationApplied": False,
                    "identityVerified": False,
                    "fallbackUsed": True,
                    "reason": publication.get("reason") or "card_photo_guard_blocked",
                }
            )

        return media


DEFAULT_CARD_PHOTO_GUARD = CardPhotoGuard()
