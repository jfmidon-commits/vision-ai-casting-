"""
CharacterSpecificationEngine - Transforma solicitacao natural em especificacao estruturada.

Entrada: "Mostre este talento como executivo, barba de tres dias, terno escuro e expressao seria"
Saida: CharacterSpecification estruturado

NAO gera imagem - apenas estrutura a especificacao para envio ao provider.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from uuid import UUID
import re

from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class CharacterArchetype:
    archetype: str
    age_presentation: str = "current"
    expression: str = "neutral"


@dataclass
class AppearanceChanges:
    beard: Optional[Dict[str, Any]] = None
    hair: Optional[Dict[str, Any]] = None
    makeup: Optional[Dict[str, Any]] = None
    body: Optional[Dict[str, Any]] = None


@dataclass
class Wardrobe:
    type: str
    tone: Optional[str] = None
    style: Optional[str] = None
    accessories: List[str] = field(default_factory=list)


@dataclass
class IdentityPreservation:
    face: bool = True
    body_proportions: bool = True
    skin_tone: bool = True
    eye_color: bool = True
    distinctive_features: bool = True


@dataclass
class EnvironmentContext:
    setting: Optional[str] = None
    lighting: Optional[str] = None
    era: Optional[str] = None


@dataclass
class CharacterSpecification:
    """Especificacao estruturada de personagem."""
    character: CharacterArchetype
    appearance_changes: AppearanceChanges
    wardrobe: Wardrobe
    identity_preservation: IdentityPreservation
    environment: EnvironmentContext
    raw_input: str = ""
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "character": {"archetype": self.character.archetype, "age_presentation": self.character.age_presentation, "expression": self.character.expression},
            "appearance_changes": {k: v for k, v in {"beard": self.appearance_changes.beard, "hair": self.appearance_changes.hair, "makeup": self.appearance_changes.makeup, "body": self.appearance_changes.body}.items() if v is not None},
            "wardrobe": {"type": self.wardrobe.type, "tone": self.wardrobe.tone, "style": self.wardrobe.style, "accessories": self.wardrobe.accessories},
            "identity_preservation": {"face": self.identity_preservation.face, "body_proportions": self.identity_preservation.body_proportions, "skin_tone": self.identity_preservation.skin_tone, "eye_color": self.identity_preservation.eye_color, "distinctive_features": self.identity_preservation.distinctive_features},
            "environment": {"setting": self.environment.setting, "lighting": self.environment.lighting, "era": self.environment.era},
            "raw_input": self.raw_input,
            "confidence": self.confidence,
        }


class CharacterSpecificationEngine:
    ARCHETYPES = {
        "executivo": "executive", "executive": "executive", "ceo": "executive", "empresario": "executive", "businessman": "executive", "businesswoman": "executive",
        "artista": "artist", "artist": "artist", "pintor": "artist", "musico": "artist", "atleta": "athlete", "athlete": "athlete", "esportista": "athlete",
        "vilao": "villain", "villain": "villain", "antagonista": "villain", "heroi": "hero", "hero": "hero", "protagonista": "hero", "cientista": "scientist", "scientist": "scientist",
        "medico": "doctor", "doctor": "doctor", "medica": "doctor", "policial": "police", "police": "police", "detetive": "police", "militar": "military", "military": "military", "soldado": "military",
        "professor": "teacher", "teacher": "teacher", "academico": "teacher",
    }
    EXPRESSIONS = {"serio": "serious", "seria": "serious", "serious": "serious", "feliz": "happy", "happy": "happy", "sorridente": "happy", "triste": "sad", "sad": "sad", "intenso": "intense", "intense": "intense", "contemplativo": "contemplative", "contemplative": "contemplative", "neutro": "neutral", "neutral": "neutral", "raiva": "angry", "angry": "angry", "furioso": "angry", "surpreso": "surprised", "surprised": "surprised"}
    BEARD_TYPES = {"barba de tres dias": {"type": "stubble", "length_days": 3}, "barba de 3 dias": {"type": "stubble", "length_days": 3}, "barba curta": {"type": "short_beard", "length_days": 7}, "barba media": {"type": "medium_beard", "length_days": 14}, "barba longa": {"type": "long_beard", "length_days": 30}, "barba raspada": {"type": "clean_shaven", "length_days": 0}, "sem barba": {"type": "clean_shaven", "length_days": 0}, "bigode": {"type": "mustache_only", "length_days": 14}}
    WARDROBE_TYPES = {
        "terno escuro": "business_suit", "terno": "business_suit", "business_suit": "business_suit", "suit": "business_suit",
        "roupa esportiva": "athletic", "roupa esportivo": "athletic", "esportiva": "athletic", "esportivo": "athletic", "athletic": "athletic",
        "jaleco branco": "uniform", "jaleco": "uniform", "uniforme": "uniform", "uniform": "uniform",
        "roupa casual": "casual", "casual": "casual", "roupa formal": "formal", "formal": "formal", "fantasia": "costume", "costume": "costume",
    }
    WARDROBE_TONES = {"escuro": "dark", "dark": "dark", "escura": "dark", "claro": "light", "light": "light", "clara": "light", "vibrante": "vibrant", "vibrant": "vibrant", "neutro": "neutral", "neutral": "neutral"}

    def __init__(self): self.specifications_generated = 0

    async def parse_request(self, natural_language: str, profile_id: Optional[UUID] = None, identity_traits: Optional[Dict] = None) -> CharacterSpecification:
        text_lower = natural_language.lower()
        character = CharacterArchetype(self._extract_archetype(text_lower), self._extract_age_presentation(text_lower), self._extract_expression(text_lower))
        appearance_changes = self._extract_appearance_changes(text_lower)
        wardrobe = self._extract_wardrobe(text_lower)
        environment = self._extract_environment(text_lower)
        spec = CharacterSpecification(character, appearance_changes, wardrobe, IdentityPreservation(), environment, natural_language, self._calculate_confidence(text_lower, character, appearance_changes, wardrobe, environment))
        self.specifications_generated += 1
        logger.info(f"CharacterSpecification generated: archetype={character.archetype}, confidence={spec.confidence:.2f}")
        return spec

    async def validate_specification(self, spec: CharacterSpecification, identity_traits: Dict[str, Any]) -> Dict[str, Any]:
        warnings = []
        if spec.appearance_changes.body:
            body_changes = spec.appearance_changes.body
            if "height" in str(body_changes).lower(): warnings.append("WARNING: Attempting to change height - permanent identity trait")
            if "bone_structure" in str(body_changes).lower(): warnings.append("WARNING: Attempting to change bone structure - permanent identity trait")
        return {"valid": len([w for w in warnings if w.startswith("WARNING")]) == 0, "warnings": warnings, "identity_preserved": spec.identity_preservation.face and spec.identity_preservation.body_proportions, "recommendation": "Specification is valid" if not warnings else "Review warnings before generation"}

    def _extract_archetype(self, text):
        for keyword, value in self.ARCHETYPES.items():
            if keyword in text: return value
        return "generic"
    def _extract_expression(self, text):
        for keyword, value in self.EXPRESSIONS.items():
            if keyword in text: return value
        return "neutral"
    def _extract_age_presentation(self, text):
        for pattern in [r"(\d+)\s*anos?", r"mais\s*(novo|nova|jovem|velho|velha)", r"mais\s*nov"]:
            match = re.search(pattern, text)
            if match:
                if "nov" in match.group(0) or "jovem" in match.group(0): return "younger"
                if "velh" in match.group(0): return "older"
                return match.group(1)
        return "current"
    def _extract_appearance_changes(self, text):
        changes = AppearanceChanges()
        for keyword, spec in self.BEARD_TYPES.items():
            if keyword in text: changes.beard = spec; break
        for pattern in [r"cabelo\s+(\w+)", r"careca", r"calvo"]:
            match = re.search(pattern, text)
            if match:
                changes.hair = {"style": "bald", "length": "none"} if match.group(0) in ["careca", "calvo"] else {"style": match.group(1), "length": match.group(1)}; break
        return changes
    def _extract_wardrobe(self, text):
        wardrobe_type, tone, accessories = "casual", None, []
        for keyword, value in self.WARDROBE_TYPES.items():
            if keyword in text: wardrobe_type = value; break
        for keyword, value in self.WARDROBE_TONES.items():
            if keyword in text: tone = value; break
        for acc in ["oculos", "relogio", "brinco", "colar", "gravata", "bone", "chapeu"]:
            if acc in text: accessories.append(acc)
        return Wardrobe(type=wardrobe_type, tone=tone, accessories=accessories)
    def _extract_environment(self, text):
        settings = {"escritorio": "office", "office": "office", "rua": "street", "street": "street", "estudio": "studio", "studio": "studio", "natureza": "nature", "nature": "nature", "casa": "home", "home": "home"}
        lightings = {"luz natural": "natural", "natural": "natural", "luz de estudio": "studio", "studio": "studio", "dramatica": "dramatic", "dramatic": "dramatic", "suave": "soft", "soft": "soft"}
        setting = next((v for k,v in settings.items() if k in text), None)
        lighting = next((v for k,v in lightings.items() if k in text), None)
        return EnvironmentContext(setting=setting, lighting=lighting)
    def _calculate_confidence(self, text, character, appearance, wardrobe, environment):
        score = 0.0
        if character.archetype != "generic": score += 0.3
        if character.expression != "neutral": score += 0.1
        if appearance.beard or appearance.hair: score += 0.2
        if wardrobe.type != "casual": score += 0.2
        if wardrobe.tone: score += 0.1
        if environment.setting or environment.lighting: score += 0.1
        return min(1.0, score + 0.1)
