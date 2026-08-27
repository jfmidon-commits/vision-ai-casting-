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
    "llm_unavailable": "O serviço de interpretação avançada estava temporariamente indisponível.",
    "llm_unavailable_rule_based_recommendations": "A interpretação avançada estava indisponível; as opções abaixo foram geradas por regras conservadoras usando apenas medições confirmadas.",
    "fallback_no_grounded_face_shape": "Sem formato facial medido, o sistema não gerou recomendações de contingência.",
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
        return "O serviço de interpretação encontrou uma limitação técnica nesta sessão."
    return "Uma parte da análise não pôde ser confirmada com segurança."


def _confidence_note(confidence: Any, has_measured: bool) -> str:
    try:
        value = float(confidence)
    except (TypeError, ValueError):
        value = 0.0
    if not has_measured or value < 0.5:
        return "A análise tem base limitada; considere novas fotos antes de decidir o corte."
    if value < 0.75:
        return "A análise tem uma base razoável, com alguns pontos ainda não confirmados."
    return "A análise tem boa base nos dados disponíveis desta sessão."


def _professional_positioning(name: str, face_shape: Optional[str]) -> str:
    if face_shape:
        return f"A opção {name} foi mantida por ser coerente com o formato facial {face_shape} identificado nesta sessão."
    return f"A opção {name} foi mantida por estar entre as recomendações validadas pelo analisador."


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

    measured = source.get("measured_data_used") if isinstance(source.get("measured_data_used"), dict) else {}
    current_hair = source.get("current_hair") if isinstance(source.get("current_hair"), dict) else {}
    limitations_raw = _as_string_list(source.get("limitations"))
    limitations: List[str] = []
    for item in limitations_raw:
        translated = _translate_limitation(item)
        if translated not in limitations:
            limitations.append(translated)

    face_shape = _clean_text(measured.get("face_shape")) or _clean_text(source.get("face_shape_category"))
    hair_density = _clean_text(measured.get("hair_density")) or _clean_text(current_hair.get("density"))
    hairline = _clean_text(measured.get("hairline")) or _clean_text(current_hair.get("hairline"))
    current_summary = _clean_text(current_hair.get("summary"))
    primary_justification = _clean_text(source.get("primary_justification"))

    attention_points = list(limitations)
    if not hair_density and "A densidade do cabelo não pôde ser medida com confiança suficiente." not in attention_points:
        attention_points.append("A densidade do cabelo não pôde ser medida com confiança suficiente.")
    if not hairline and "A linha frontal do cabelo não pôde ser confirmada com confiança suficiente." not in attention_points:
        attention_points.append("A linha frontal do cabelo não pôde ser confirmada com confiança suficiente.")
    if not face_shape and "O formato facial não pôde ser confirmado com dados medidos nesta sessão." not in attention_points:
        attention_points.append("O formato facial não pôde ser confirmado com dados medidos nesta sessão.")

    measured_labels: List[str] = []
    if face_shape:
        measured_labels.append(f"formato facial: {face_shape}")
    if hair_density:
        measured_labels.append(f"densidade do cabelo: {hair_density}")
    if hairline:
        measured_labels.append(f"linha frontal: {hairline}")

    if primary:
        why = primary_justification or f"{primary} está entre as recomendações sustentadas pelos dados disponíveis desta sessão."
        primary_recommendation: Optional[Dict[str, Any]] = {
            "name": primary,
            "why_it_works": why,
            "visual_effect": "Sugestão estética baseada na recomendação validada; a aparência final depende da execução profissional e do cabelo real.",
            "professional_positioning": _professional_positioning(primary, face_shape),
            "maintenance_level": "não determinado",
            "barber_instruction": "Use o nome do corte como referência e ajuste comprimentos ao cabelo real; esta sessão não mediu comprimentos em cm/mm.",
        }
    else:
        primary_recommendation = None

    alternatives = []
    for name in hairstyles:
        if name == primary:
            continue
        alternatives.append({
            "name": name,
            "why_it_works": f"{name} aparece na lista de recomendações validadas desta sessão.",
            "best_use_case": "Alternativa estética ao corte principal, a ser comparada com preferência pessoal e manutenção desejada.",
            "maintenance_level": "não determinado",
        })

    executive_summary = (
        "A análise utilizou " + ", ".join(measured_labels) + "."
        if measured_labels
        else "A sessão não reuniu medições suficientes para uma síntese facial e capilar completa."
    )
    if primary:
        executive_summary += f" A recomendação principal validada é {primary}."

    status = "ready" if primary else "insufficient_grounded_data"

    return {
        "status": status,
        "executive_summary": executive_summary,
        "current_hair_assessment": {
            "summary": current_summary or "Avaliação do cabelo atual limitada pelos dados disponíveis.",
            "strengths": [item for item in measured_labels if item.startswith("densidade") or item.startswith("linha frontal")],
            "attention_points": attention_points,
        },
        "primary_recommendation": primary_recommendation,
        "alternative_hairstyles": alternatives,
        "barber_brief": {
            "recommendation_name": primary,
            "grounded_in": measured_labels,
            "top": "comprimento não medido nesta sessão",
            "sides": "comprimento não medido nesta sessão",
            "back": "comprimento não medido nesta sessão",
            "fringe": "comprimento não medido nesta sessão",
            "texture": _clean_text(current_hair.get("texture")) or "não determinada",
            "finish": "definir com o profissional conforme o corte escolhido",
            "avoid": "não alterar características além do necessário para executar o corte escolhido",
            "note": "Este brief separa fatos medidos de recomendações estéticas; cm/mm não são inventados.",
        },
        "professional_image": {
            "actor_casting": "Priorize coerência com o perfil do personagem; a recomendação de corte é uma base, não uma exigência de casting.",
            "commercial_model": "Priorize leitura limpa e versátil, preservando características reconhecíveis da pessoa.",
            "corporate_institutional": "Priorize acabamento controlado e apresentação consistente com o ambiente profissional.",
            "lifestyle_advertising": "A recomendação pode ser adaptada para um acabamento mais natural, mantendo a identidade visual da pessoa.",
        },
        "limitations": limitations,
        "confidence_note": _confidence_note(source.get("confidence"), bool(measured_labels)),
    }
