"""Grounded presentation layer for visagism results.

This module does not decide haircuts and does not invent measurements. It only
translates the already-grounded analyzer output into a stable, user-facing
contract that can be persisted in Analysis.visagism and consumed by mobile.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


_LIMITATION_COPY = {
    "all_photos_rejected_by_triage": "As fotos enviadas não passaram na triagem automática.",
    "photo_rejected_by_triage": "A foto não passou na triagem automática.",
    "facial_result_is_mock": "A análise do formato facial não pôde ser confirmada com dados reais desta sessão.",
    "grooming_analyzer_not_available": "Não foi possível avaliar cabelo e acabamento com dados suficientes.",
    "colorimetry_analyzer_not_available": "A colorimetria não pôde ser confirmada nesta sessão.",
    "photogenic_analyzer_not_available": "A qualidade fotográfica não pôde ser confirmada nesta sessão.",
    "expressions_analyzer_not_available": "A análise de expressão não pôde ser confirmada nesta sessão.",
    "hair_density_not_measured": "A densidade do cabelo não pôde ser medida com confiança suficiente.",
    "hairline_not_measured": "A linha frontal do cabelo não pôde ser confirmada com confiança suficiente.",
    "face_shape_not_measured": "O formato facial não pôde ser confirmado com dados medidos nesta sessão.",
    "no_grounded_hairstyles": "Não houve dados suficientes para recomendar um corte com segurança.",
    "llm_unavailable": "A interpretação avançada não estava disponível nesta sessão.",
    "llm_unavailable_rule_based_recommendations": "A interpretação avançada não estava disponível; as recomendações foram montadas de forma conservadora a partir das medições confirmadas.",
    "llm_unavailable_personalized_rule_based_recommendations": "A interpretação avançada não estava disponível; as recomendações foram personalizadas apenas com as medições faciais e capilares confirmadas desta sessão.",
    "fallback_insufficient_personalization": "As medições confirmadas não foram suficientes para diferenciar recomendações com segurança; por isso nenhuma lista genérica foi exibida.",
    "fallback_no_grounded_face_shape": "Sem formato facial medido, o sistema não gerou recomendações de contingência.",
}

_FACE_SHAPE_LABELS = {
    "round": "redondo",
    "redondo": "redondo",
    "oval": "oval",
    "square": "quadrado",
    "quadrado": "quadrado",
    "heart": "coração",
    "coracao": "coração",
    "coração": "coração",
    "diamond": "diamante",
    "diamante": "diamante",
    "oblong": "oblongo",
    "oblongo": "oblongo",
    "triangular": "triangular",
    "triangle": "triangular",
}

_RULE_BASED_HAIRCUT_RATIONALES = {
    "Quiff texturizado": "O volume concentrado no topo ajuda a alongar visualmente o rosto, enquanto laterais mais controladas evitam ampliar ainda mais a largura aparente.",
    "Side Part com volume no topo": "A divisão lateral cria assimetria visual e o volume no topo acrescenta altura, duas características úteis para equilibrar um rosto redondo.",
    "Pompadour moderado": "O volume vertical do pompadour acrescenta altura ao conjunto sem exigir excesso de largura nas laterais.",
    "Undercut com topo alongado": "O contraste entre laterais controladas e topo mais alongado reforça linhas verticais e ajuda a reduzir a sensação de largura do rosto.",
    "Crew Cut com laterais mais baixas": "A leitura mais limpa nas laterais mantém o contorno organizado; um pouco mais de presença no topo evita deixar o rosto visualmente mais largo.",
}

_RULE_BASED_BARBER_GUIDANCE = {
    "Quiff texturizado": {
        "top": "preservar comprimento suficiente para criar volume e textura no topo",
        "sides": "manter mais controladas que o topo, com transição suave",
        "back": "acompanhar o controle das laterais e manter o contorno limpo",
        "fringe": "direcionar para cima e levemente para trás para reforçar altura",
        "texture": "texturizada, evitando acabamento totalmente achatado",
        "finish": "natural, com o volume concentrado no topo",
        "avoid": "excesso de volume nas laterais ou topo completamente achatado",
    },
    "Side Part com volume no topo": {
        "top": "preservar volume moderado no topo para permitir a divisão lateral",
        "sides": "manter controladas para destacar a diferença de altura do topo",
        "back": "seguir a mesma transição das laterais, sem criar largura extra",
        "fringe": "integrar à divisão lateral, mantendo movimento e altura",
        "texture": "controlada, com movimento suficiente para a risca lateral",
        "finish": "definido sem ficar rígido ou excessivamente marcado",
        "avoid": "laterais volumosas no mesmo nível do topo",
    },
    "Pompadour moderado": {
        "top": "preservar comprimento para construir elevação frontal moderada",
        "sides": "manter mais enxutas que o topo, com transição proporcional",
        "back": "manter alinhado ao desenho das laterais",
        "fringe": "elevar e direcionar para trás sem exagerar na altura",
        "texture": "mais polida, mas sem eliminar totalmente o movimento natural",
        "finish": "estruturado com aparência leve",
        "avoid": "volume excessivo nas laterais ou pompadour muito largo",
    },
    "Undercut com topo alongado": {
        "top": "preservar comprimento e movimento para criar contraste com as laterais",
        "sides": "manter visivelmente mais controladas que o topo",
        "back": "acompanhar o contraste das laterais com acabamento limpo",
        "fringe": "integrar ao topo, podendo ser direcionada para trás ou para o lado",
        "texture": "texturizada ou natural, conforme o comportamento real do cabelo",
        "finish": "contraste limpo entre topo e laterais",
        "avoid": "dar volume horizontal às laterais",
    },
    "Crew Cut com laterais mais baixas": {
        "top": "manter um pouco mais de presença que nas laterais, sem necessidade de altura exagerada",
        "sides": "manter baixas e organizadas para reduzir largura visual",
        "back": "seguir o mesmo desenho limpo das laterais",
        "fringe": "curta e integrada ao topo, sem criar largura frontal",
        "texture": "natural e discreta",
        "finish": "limpo e de baixa manutenção",
        "avoid": "deixar laterais tão cheias quanto o topo",
    },
}


def _clean_text(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text or text.lower() in {"não medido", "nao medido", "none", "null"}:
        return None
    return text


def _as_string_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def _face_shape_label(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    return _FACE_SHAPE_LABELS.get(value.strip().lower(), value.strip())


def _translate_limitation(code: Any) -> str:
    if not isinstance(code, str) or not code.strip():
        return "Uma parte da análise não pôde ser confirmada com segurança."
    raw = code.strip()
    if raw in _LIMITATION_COPY:
        return _LIMITATION_COPY[raw]
    if raw.startswith("fewer_than_5_grounded_hairstyles:"):
        return "Foram encontradas menos de cinco recomendações com base suficiente nesta sessão."
    if raw == "primary_hairstyle_not_in_recommendations":
        return "A recomendação principal foi ajustada para uma opção presente na lista validada."
    if raw.lower().startswith("error:"):
        return (
            "O serviço de interpretação encontrou uma limitação técnica nesta sessão."
        )
    return "Uma parte da análise não pôde ser confirmada com segurança."


def _confidence_note(confidence: Any, has_measured: bool) -> str:
    try:
        value = float(confidence)
    except (TypeError, ValueError):
        value = 0.0
    if not has_measured or value < 0.5:
        return "A análise tem base limitada; considere novas fotos antes de decidir o corte."
    if value < 0.75:
        return (
            "A análise tem uma base razoável, com alguns pontos ainda não confirmados."
        )
    return "A análise tem boa base nos dados disponíveis desta sessão."


def _professional_positioning(name: str, face_shape: Optional[str]) -> str:
    if face_shape:
        return f"A opção {name} foi mantida por ser coerente com o formato facial {face_shape} identificado nesta sessão."
    return f"A opção {name} foi mantida por estar entre as recomendações validadas pelo analisador."


def _barber_guidance(
    name: Optional[str], current_hair: Dict[str, Any]
) -> Dict[str, str]:
    if name and name in _RULE_BASED_BARBER_GUIDANCE:
        return dict(_RULE_BASED_BARBER_GUIDANCE[name])
    return {
        "top": "ajustar o comprimento ao cabelo real e ao desenho do corte escolhido",
        "sides": "definir a transição de acordo com o corte escolhido e o caimento real",
        "back": "acompanhar o desenho das laterais e o formato natural da cabeça",
        "fringe": "adaptar ao corte escolhido e ao comportamento natural do cabelo",
        "texture": _clean_text(current_hair.get("texture"))
        or "avaliar presencialmente antes de finalizar",
        "finish": "definir com o profissional conforme o corte escolhido",
        "avoid": "não inventar medidas nem forçar um acabamento incompatível com o cabelo real",
    }


def build_visagism_interpretation(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Build the stable presentation contract from a raw analyzer result.

    Haircut names are copied exactly from ``recommended_hairstyles`` and no
    missing measurement is filled in.
    """
    source = analysis if isinstance(analysis, dict) else {}
    hairstyles = _as_string_list(source.get("recommended_hairstyles"))
    primary = _clean_text(source.get("primary_hairstyle"))
    if primary not in hairstyles:
        primary = hairstyles[0] if hairstyles else None

    measured = (
        source.get("measured_data_used")
        if isinstance(source.get("measured_data_used"), dict)
        else {}
    )
    current_hair = (
        source.get("current_hair")
        if isinstance(source.get("current_hair"), dict)
        else {}
    )
    data_source = (
        source.get("data_source") if isinstance(source.get("data_source"), dict) else {}
    )
    rule_based = data_source.get("rule_based_interpretation") is True

    limitations_raw = _as_string_list(source.get("limitations"))
    limitations: List[str] = []
    for item in limitations_raw:
        translated = _translate_limitation(item)
        if translated not in limitations:
            limitations.append(translated)

    raw_face_shape = _clean_text(measured.get("face_shape")) or _clean_text(
        source.get("face_shape_category")
    )
    face_shape = _face_shape_label(raw_face_shape)
    hair_density = _clean_text(measured.get("hair_density")) or _clean_text(
        current_hair.get("density")
    )
    hairline = _clean_text(measured.get("hairline")) or _clean_text(
        current_hair.get("hairline")
    )
    current_summary = _clean_text(current_hair.get("summary"))
    primary_justification = _clean_text(source.get("primary_justification"))

    attention_points = list(limitations)
    if (
        not hair_density
        and "A densidade do cabelo não pôde ser medida com confiança suficiente."
        not in attention_points
    ):
        attention_points.append(
            "A densidade do cabelo não pôde ser medida com confiança suficiente."
        )
    if (
        not hairline
        and "A linha frontal do cabelo não pôde ser confirmada com confiança suficiente."
        not in attention_points
    ):
        attention_points.append(
            "A linha frontal do cabelo não pôde ser confirmada com confiança suficiente."
        )
    if (
        not face_shape
        and "O formato facial não pôde ser confirmado com dados medidos nesta sessão."
        not in attention_points
    ):
        attention_points.append(
            "O formato facial não pôde ser confirmado com dados medidos nesta sessão."
        )

    measured_labels: List[str] = []
    if face_shape:
        measured_labels.append(f"formato facial: {face_shape}")
    if hair_density:
        measured_labels.append(f"densidade do cabelo: {hair_density}")
    if hairline:
        measured_labels.append(f"linha frontal: {hairline}")

    if primary:
        if rule_based and primary in _RULE_BASED_HAIRCUT_RATIONALES:
            why = _RULE_BASED_HAIRCUT_RATIONALES[primary]
        else:
            why = (
                primary_justification
                or f"{primary} está entre as recomendações sustentadas pelos dados disponíveis desta sessão."
            )
        primary_recommendation: Optional[Dict[str, Any]] = {
            "name": primary,
            "why_it_works": why,
            "visual_effect": "Sugestão estética baseada nos dados confirmados; a aparência final depende da execução profissional e do comportamento real do cabelo.",
            "professional_positioning": _professional_positioning(primary, face_shape),
            "maintenance_level": "avaliar com o profissional",
            "barber_instruction": "Use estas orientações como referência visual e ajuste o corte ao cabelo real, sem assumir comprimentos que não foram medidos.",
        }
    else:
        primary_recommendation = None

    alternatives = []
    for name in hairstyles:
        if name == primary:
            continue
        if rule_based and name in _RULE_BASED_HAIRCUT_RATIONALES:
            why_it_works = _RULE_BASED_HAIRCUT_RATIONALES[name]
        else:
            why_it_works = f"{name} aparece entre as recomendações sustentadas pelos dados desta sessão."
        alternatives.append(
            {
                "name": name,
                "why_it_works": why_it_works,
                "best_use_case": "Alternativa estética ao corte principal, a ser comparada com preferência pessoal e manutenção desejada.",
                "maintenance_level": "avaliar com o profissional",
            }
        )

    executive_summary = (
        "A análise utilizou " + ", ".join(measured_labels) + "."
        if measured_labels
        else "A sessão não reuniu medições suficientes para uma síntese facial e capilar completa."
    )
    if primary:
        executive_summary += f" A recomendação principal é {primary}."

    if primary and rule_based:
        status = "partial_grounded"
    elif primary:
        status = "ready"
    elif (
        data_source.get("llm_interpretation") is False
        and data_source.get("measured") is True
    ):
        status = "service_limited"
    else:
        status = "insufficient_grounded_data"
    brief = _barber_guidance(primary, current_hair)

    return {
        "status": status,
        "executive_summary": executive_summary,
        "current_hair_assessment": {
            "summary": current_summary
            or "Avaliação do cabelo atual limitada pelos dados disponíveis.",
            "strengths": [
                item
                for item in measured_labels
                if item.startswith("densidade") or item.startswith("linha frontal")
            ],
            "attention_points": attention_points,
        },
        "primary_recommendation": primary_recommendation,
        "alternative_hairstyles": alternatives,
        "barber_brief": {
            "recommendation_name": primary,
            "grounded_in": measured_labels,
            "top": brief["top"],
            "sides": brief["sides"],
            "back": brief["back"],
            "fringe": brief["fringe"],
            "texture": brief["texture"],
            "finish": brief["finish"],
            "avoid": brief["avoid"],
            "note": "As orientações descrevem o efeito visual do corte sem inventar comprimentos em cm/mm; o ajuste final deve ser feito no cabelo real.",
        },
        "professional_image": {
            "actor_casting": "Priorize coerência com o perfil do personagem; a recomendação de corte é uma base, não uma exigência de casting.",
            "commercial_model": "Priorize leitura limpa e versátil, preservando características reconhecíveis da pessoa.",
            "corporate_institutional": "Priorize acabamento controlado e apresentação consistente com o ambiente profissional.",
            "lifestyle_advertising": "A recomendação pode ser adaptada para um acabamento mais natural, mantendo a identidade visual da pessoa.",
        },
        "limitations": limitations,
        "confidence_note": _confidence_note(
            source.get("confidence"), bool(measured_labels)
        ),
    }
