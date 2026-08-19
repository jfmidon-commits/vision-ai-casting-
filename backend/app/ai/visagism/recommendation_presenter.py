"""User-facing presentation for technical visagism haircut recommendations.

The rule engine intentionally keeps stable technical identifiers. This module
converts those identifiers into names and instructions a client, stylist or
barber can understand without losing traceability.
"""

from typing import Any, Dict, Iterable, List


STYLE_CATALOG: Dict[str, Dict[str, str]] = {
    "volume_on_top": {
        "display_name": "Topo texturizado com volume e taper suave",
        "barber_instructions": (
            "Manter 6-9 cm no topo, com mais comprimento na regiao frontal; "
            "texturizar com tesoura para criar volume sem formar bloco. Fazer "
            "taper baixo/suave nas laterais e nuca, sem raspar alto e sem criar "
            "volume junto a mandibula. Finalizar o topo para cima e levemente para tras."
        ),
        "styling": "Secador direcionando a raiz para cima; finalizar com pasta ou pomada fosca leve.",
    },
    "layered_top": {
        "display_name": "Topo em camadas com taper classico",
        "barber_instructions": (
            "Topo medio em camadas, preservando comprimento frontal e movimento. "
            "Laterais progressivamente mais curtas em taper classico, mantendo transicao suave."
        ),
        "styling": "Modelar com os dedos, criando separacao e leve volume frontal.",
    },
    "side_swept": {
        "display_name": "Side swept texturizado com laterais contidas",
        "barber_instructions": (
            "Preservar comprimento suficiente no topo para pentear diagonalmente para um lado. "
            "Criar textura leve; taper nas laterais, evitando volume na altura da mandibula."
        ),
        "styling": "Secar em diagonal e usar produto de fixacao leve a media, sem efeito pesado.",
    },
    "asymmetrical": {
        "display_name": "Topo assimetrico texturizado com taper baixo",
        "barber_instructions": (
            "Criar assimetria discreta no topo, com um lado frontal ligeiramente mais longo. "
            "Manter laterais limpas em taper baixo e acabamento natural, sem undercut agressivo."
        ),
        "styling": "Direcionar o topo para um lado, mantendo textura e volume sem rigidez.",
    },
    "height_at_crown": {
        "display_name": "Volume de coroa com frente elevada",
        "barber_instructions": (
            "Preservar comprimento no topo e coroa para gerar altura controlada, conectando "
            "com a regiao frontal. Laterais em taper suave e sem excesso de peso."
        ),
        "styling": "Levantar raiz na coroa e frontal com secador; acabamento fosco e natural.",
    },
    "textured_top": {
        "display_name": "French crop longo/texturizado com topo elevado",
        "barber_instructions": (
            "Topo texturizado e relativamente longo, sem franja pesada reta. Manter frente aberta "
            "ou elevada; laterais em taper baixo para preservar equilibrio facial."
        ),
        "styling": "Texturizar com pasta fosca, mantendo movimento e a testa parcialmente aberta.",
    },
}


def _value(value: Any) -> Any:
    return getattr(value, "value", value)


def present_recommendation(item: Any) -> Dict[str, Any]:
    """Convert a recommendation model/dict into a stable user-facing payload."""
    technical_name = item.get("name") if isinstance(item, dict) else getattr(item, "name", "")
    catalog = STYLE_CATALOG.get(
        technical_name,
        {
            "display_name": technical_name.replace("_", " ").title(),
            "barber_instructions": (
                "Adaptar o corte ao formato facial e preservar a distribuicao de volume indicada pelo motor."
            ),
            "styling": "Finalizacao natural, ajustada a textura real do cabelo.",
        },
    )

    def field(name: str, default: Any = None) -> Any:
        if isinstance(item, dict):
            return item.get(name, default)
        return getattr(item, name, default)

    justification = field("justification", "") or ""
    hair_data_complete = "unknown" not in justification.lower()

    return {
        "rank": field("rank"),
        "technical_id": technical_name,
        "display_name": catalog["display_name"],
        "why_it_works": justification,
        "barber_instructions": catalog["barber_instructions"],
        "styling": catalog["styling"],
        "volume_distribution": field("volume_distribution"),
        "forehead_exposure": _value(
            field("forehead_exposure_recommendation", field("forehead_exposure"))
        ),
        "side_treatment": _value(field("side_treatment")),
        "maintenance_frequency": field("maintenance_frequency"),
        "maintenance_difficulty": _value(field("maintenance_difficulty")),
        "confidence": field("confidence"),
        "hair_data_complete": hair_data_complete,
        "hair_data_note": (
            None
            if hair_data_complete
            else "Textura e/ou espessura nao foram confirmadas; validar esses dados antes do corte para refinamento final."
        ),
    }


def present_recommendations(items: Iterable[Any]) -> List[Dict[str, Any]]:
    """Present recommendations preserving their original ranking."""
    return [present_recommendation(item) for item in items]
