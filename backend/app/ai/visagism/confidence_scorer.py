"""
backend/app/ai/visagism/confidence_scorer.py

Sistema de confidence scoring do VisagismAgent.

Calcula scores de confianca em multiplos niveis:
- Por evidencia individual
- Por conclusao (agregado de evidencias)
- Por modulo do pipeline
- Global da analise

O sistema nao apenas retorna um numero: explica POR QUE aquele
confidence foi atribuido, permitindo ao usuario humano avaliar
a credibilidade de cada recomendacao.
"""

import math
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from app.ai.visagism.schemas import ConfidenceLevel


@dataclass
class ConfidenceBreakdown:
    """Decomposicao detalhada de um confidence score."""
    score: float
    level: ConfidenceLevel
    factors: List[Dict[str, Any]]
    explanation: str


class ConfidenceScorer:
    """
    Motor de calculo de confidence scores.
    
    Principios:
    1. Confidence e proporcional a quantidade e qualidade das evidencias
    2. Multiplas fontes independentes aumentam confidence
    3. Inferencias sem medicoes diretas reduzem confidence
    4. Fotos de baixa qualidade reduzem confidence do modulo
    5. Confidence nunca e 1.0 (sempre ha incerteza)
    """
    
    # Pesos para diferentes fontes de evidencia
    SOURCE_WEIGHTS = {
        "mediapipe_landmark": 0.95,
        "mediapipe_mesh": 0.90,
        "deepface_analysis": 0.85,
        "rekognition": 0.80,
        "computed_ratio": 0.75,
        "llm_vision": 0.70,
        "human_verified": 1.0,
        "inferred": 0.40,
        "unknown": 0.20,
    }
    
    # Penalidades
    FEW_PHOTOS_PENALTY = 0.85  # < 3 fotos usaveis
    SINGLE_PHOTO_PENALTY = 0.60  # apenas 1 foto
    LOW_QUALITY_PENALTY = 0.70  # foto com qualidade < 0.5
    NO_POSTERIOR_PENALTY = 0.90  # falta angulo posterior
    NO_PROFILE_PENALTY = 0.85  # falta perfil
    INFERENCE_HEAVY_PENALTY = 0.75  # > 50% das conclusoes sao inferidas
    
    def __init__(self):
        self._factors: List[Dict[str, Any]] = []
    
    def score_evidence(
        self,
        source: str,
        measurement_quality: float,  # 0-1, quao precisa e a medicao
        consistency: float = 1.0,  # 0-1, consistencia entre multiplas fontes
    ) -> ConfidenceBreakdown:
        """
        Calcula o confidence de uma evidencia individual.
        
        Args:
            source: Fonte da evidencia
            measurement_quality: Qualidade da medicao (0-1)
            consistency: Consistencia com outras fontes (0-1)
        """
        source_weight = self.SOURCE_WEIGHTS.get(source, 0.5)
        
        # Score base = peso da fonte * qualidade da medicao * consistencia
        score = source_weight * measurement_quality * consistency
        
        # Nunca 1.0
        score = min(0.98, score)
        
        factors = [
            {"factor": "source_reliability", "weight": source_weight, "description": f"Fonte: {source}"},
            {"factor": "measurement_quality", "value": measurement_quality},
            {"factor": "cross_source_consistency", "value": consistency},
        ]
        
        level = self._score_to_level(score)
        explanation = self._explain_evidence(source, measurement_quality, consistency, score)
        
        return ConfidenceBreakdown(score=round(score, 3), level=level, factors=factors, explanation=explanation)
    
    def score_conclusion(
        self,
        evidence_scores: List[float],
        conclusion_type: str,  # "measurement", "proportion", "interpretation", "recommendation"
        has_direct_evidence: bool = True,
    ) -> ConfidenceBreakdown:
        """
        Calcula o confidence de uma conclusao a partir das evidencias que a fundamentam.
        
        Args:
            evidence_scores: Lista de confidence scores das evidencias de base
            conclusion_type: Tipo da conclusao
            has_direct_evidence: Se ha evidencia direta (vs. pura inferencia)
        """
        if not evidence_scores:
            return ConfidenceBreakdown(
                score=0.0,
                level=ConfidenceLevel.INSUFFICIENT_DATA,
                factors=[{"factor": "no_evidence", "description": "Nenhuma evidencia disponivel"}],
                explanation="Conclusao sem evidencias de suporte."
            )
        
        # Media geometrica das evidencias
        product = 1.0
        for s in evidence_scores:
            product *= max(0.01, s)
        geometric_mean = product ** (1.0 / len(evidence_scores))
        
        # Penalidade por falta de evidencia direta
        direct_penalty = 1.0 if has_direct_evidence else 0.6
        
        # Penalidade por pouca evidencia
        evidence_penalty = min(1.0, len(evidence_scores) / 3.0)
        
        # Penalidade por tipo de conclusao
        type_weights = {
            "measurement": 1.0,
            "proportion": 0.95,
            "interpretation": 0.85,
            "recommendation": 0.75,
        }
        type_weight = type_weights.get(conclusion_type, 0.8)
        
        score = geometric_mean * direct_penalty * evidence_penalty * type_weight
        score = min(0.98, score)
        
        factors = [
            {"factor": "evidence_geometric_mean", "value": round(geometric_mean, 3)},
            {"factor": "evidence_count", "value": len(evidence_scores)},
            {"factor": "direct_evidence", "value": has_direct_evidence},
            {"factor": "conclusion_type", "weight": type_weight, "type": conclusion_type},
        ]
        
        level = self._score_to_level(score)
        explanation = self._explain_conclusion(len(evidence_scores), has_direct_evidence, conclusion_type, score)
        
        return ConfidenceBreakdown(score=round(score, 3), level=level, factors=factors, explanation=explanation)
    
    def score_module(
        self,
        photo_count: int,
        usable_photo_count: int,
        avg_photo_quality: float,
        conclusion_scores: List[float],
        has_key_angles: Dict[str, bool],
    ) -> ConfidenceBreakdown:
        """
        Calcula o confidence de um modulo inteiro do pipeline.
        
        Args:
            photo_count: Total de fotos submetidas
            usable_photo_count: Fotos usaveis apos validacao
            avg_photo_quality: Qualidade media das fotos usaveis (0-1)
            conclusion_scores: Confidence scores das conclusoes do modulo
            has_key_angles: Dict indicando quais angulos chave estao presentes
        """
        factors = []
        
        # Base: media das conclusoes
        if conclusion_scores:
            base_score = sum(conclusion_scores) / len(conclusion_scores)
        else:
            base_score = 0.3
        
        factors.append({"factor": "avg_conclusion_confidence", "value": round(base_score, 3)})
        
        # Penalidade por poucas fotos
        photo_penalty = 1.0
        if usable_photo_count == 1:
            photo_penalty = self.SINGLE_PHOTO_PENALTY
            factors.append({"factor": "single_photo_penalty", "value": photo_penalty, "reason": "Apenas 1 foto usavel"})
        elif usable_photo_count < 3:
            photo_penalty = self.FEW_PHOTOS_PENALTY
            factors.append({"factor": "few_photos_penalty", "value": photo_penalty, "reason": f"Apenas {usable_photo_count} fotos usaveis"})
        else:
            factors.append({"factor": "photo_count", "value": usable_photo_count, "status": "adequado"})
        
        # Penalidade por qualidade
        quality_penalty = 1.0
        if avg_photo_quality < 0.5:
            quality_penalty = self.LOW_QUALITY_PENALTY
            factors.append({"factor": "low_quality_penalty", "value": quality_penalty, "reason": "Qualidade media baixa"})
        
        # Penalidade por angulos faltantes
        angle_penalty = 1.0
        if not has_key_angles.get("profile", False):
            angle_penalty *= self.NO_PROFILE_PENALTY
            factors.append({"factor": "missing_profile", "penalty": self.NO_PROFILE_PENALTY})
        if not has_key_angles.get("posterior", False):
            angle_penalty *= self.NO_POSTERIOR_PENALTY
            factors.append({"factor": "missing_posterior", "penalty": self.NO_POSTERIOR_PENALTY})
        
        score = base_score * photo_penalty * quality_penalty * angle_penalty
        score = min(0.98, score)
        
        level = self._score_to_level(score)
        explanation = self._explain_module(usable_photo_count, avg_photo_quality, has_key_angles, score)
        
        return ConfidenceBreakdown(score=round(score, 3), level=level, factors=factors, explanation=explanation)
    
    def score_overall(
        self,
        module_scores: Dict[str, float],
        has_critical_modules: Dict[str, bool],
        inference_ratio: float,  # proporcao de conclusoes inferidas vs. medidas
    ) -> ConfidenceBreakdown:
        """
        Calcula o confidence global da analise.
        
        Args:
            module_scores: Dict {nome_modulo: confidence}
            has_critical_modules: Dict {modulo: True/False} para modulos criticos
            inference_ratio: Proporcao de inferencias (0 = tudo medido, 1 = tudo inferido)
        """
        factors = []
        
        # Base: media ponderada dos modulos
        weights = {
            "validation": 0.10,
            "measurement": 0.25,
            "hair_analysis": 0.15,
            "multimodal": 0.15,
            "rules": 0.20,
            "recommendations": 0.15,
        }
        
        weighted_sum = 0.0
        weight_total = 0.0
        for module, score in module_scores.items():
            w = weights.get(module, 0.1)
            weighted_sum += score * w
            weight_total += w
            factors.append({"factor": f"module_{module}", "score": round(score, 3), "weight": w})
        
        base_score = weighted_sum / weight_total if weight_total > 0 else 0.3
        
        # Penalidade por modulos criticos faltantes
        critical_penalty = 1.0
        for module, present in has_critical_modules.items():
            if not present:
                critical_penalty *= 0.7
                factors.append({"factor": f"missing_critical_{module}", "penalty": 0.7})
        
        # Penalidade por excesso de inferencias
        inference_penalty = 1.0
        if inference_ratio > 0.5:
            inference_penalty = self.INFERENCE_HEAVY_PENALTY
            factors.append({
                "factor": "inference_heavy",
                "penalty": inference_penalty,
                "reason": f"{inference_ratio:.0%} das conclusoes sao inferidas",
            })
        
        score = base_score * critical_penalty * inference_penalty
        score = min(0.95, score)  # Nunca 100%
        
        level = self._score_to_level(score)
        explanation = self._explain_overall(module_scores, inference_ratio, score)
        
        return ConfidenceBreakdown(score=round(score, 3), level=level, factors=factors, explanation=explanation)
    
    def _score_to_level(self, score: float) -> ConfidenceLevel:
        """Converte um score numerico para nivel qualitativo."""
        if score > 0.95:
            return ConfidenceLevel.CERTAIN
        elif score > 0.80:
            return ConfidenceLevel.HIGH
        elif score > 0.60:
            return ConfidenceLevel.MODERATE
        elif score > 0.40:
            return ConfidenceLevel.LOW
        elif score > 0.20:
            return ConfidenceLevel.UNCERTAIN
        else:
            return ConfidenceLevel.INSUFFICIENT_DATA
    
    def _explain_evidence(
        self,
        source: str,
        measurement_quality: float,
        consistency: float,
        score: float,
    ) -> str:
        """Gera explicacao legivel para confidence de evidencia."""
        parts = []
        
        source_desc = {
            "mediapipe_landmark": "medicao direta de landmark facial",
            "mediapipe_mesh": "malha facial densa",
            "deepface_analysis": "analise por modelo de deep learning",
            "rekognition": "servico de reconhecimento facial da AWS",
            "computed_ratio": "razao computada a partir de medicoes",
            "llm_vision": "interpretacao por modelo de linguagem multimodal",
            "inferred": "inferencia sem medicao direta",
        }
        
        parts.append(f"Fonte: {source_desc.get(source, source)}")
        
        if measurement_quality > 0.9:
            parts.append("Medicao de alta precisao")
        elif measurement_quality > 0.7:
            parts.append("Medicao de precisao aceitavel")
        else:
            parts.append("Medicao de precisao limitada")
        
        if consistency < 0.8:
            parts.append("Inconsistencia detectada entre fontes")
        
        parts.append(f"Score: {score:.1%}")
        
        return "; ".join(parts)
    
    def _explain_conclusion(
        self,
        evidence_count: int,
        has_direct_evidence: bool,
        conclusion_type: str,
        score: float,
    ) -> str:
        """Gera explicacao legivel para confidence de conclusao."""
        parts = []
        
        type_desc = {
            "measurement": "medicao direta",
            "proportion": "proporcao computada",
            "interpretation": "interpretacao de padroes",
            "recommendation": "recomendacao baseada em regras",
        }
        
        parts.append(f"Tipo: {type_desc.get(conclusion_type, conclusion_type)}")
        parts.append(f"Baseada em {evidence_count} evidencia(s)")
        
        if not has_direct_evidence:
            parts.append("ATENCAO: sem evidencia direta — inferencia pura")
        
        if evidence_count < 2:
            parts.append("Pouca evidencia de suporte")
        
        parts.append(f"Score: {score:.1%}")
        
        return "; ".join(parts)
    
    def _explain_module(
        self,
        usable_photo_count: int,
        avg_photo_quality: float,
        has_key_angles: Dict[str, bool],
        score: float,
    ) -> str:
        """Gera explicacao legivel para confidence de modulo."""
        parts = []
        
        if usable_photo_count >= 5:
            parts.append(f"Protocolo completo: {usable_photo_count} fotos usaveis")
        elif usable_photo_count >= 3:
            parts.append(f"Protocolo parcial: {usable_photo_count} fotos usaveis")
        else:
            parts.append(f"Protocolo insuficiente: apenas {usable_photo_count} foto(s)")
        
        if avg_photo_quality < 0.5:
            parts.append("Qualidade das fotos compromete a analise")
        
        missing = [k for k, v in has_key_angles.items() if not v]
        if missing:
            parts.append(f"Angulos ausentes: {', '.join(missing)}")
        
        parts.append(f"Score do modulo: {score:.1%}")
        
        return "; ".join(parts)
    
    def _explain_overall(
        self,
        module_scores: Dict[str, float],
        inference_ratio: float,
        score: float,
    ) -> str:
        """Gera explicacao legivel para confidence global."""
        parts = []
        
        # Resumo dos modulos
        strong_modules = [k for k, v in module_scores.items() if v > 0.8]
        weak_modules = [k for k, v in module_scores.items() if v < 0.5]
        
        if strong_modules:
            parts.append(f"Modulos fortes: {', '.join(strong_modules)}")
        if weak_modules:
            parts.append(f"Modulos fracos: {', '.join(weak_modules)}")
        
        if inference_ratio > 0.5:
            parts.append(f"ALERTA: {inference_ratio:.0%} das conclusoes sao inferidas, nao medidas")
        elif inference_ratio > 0.3:
            parts.append(f"{inference_ratio:.0%} das conclusoes sao inferidas")
        
        if score > 0.8:
            parts.append("Analise com alta confianca geral")
        elif score > 0.6:
            parts.append("Analise com confianca moderada — recomendacoes principais sao confiaveis")
        elif score > 0.4:
            parts.append("Analise com confianca limitada — validar recomendacoes com profissional")
        else:
            parts.append("Analise com baixa confianca — insuficiente para recomendacoes definitivas")
        
        parts.append(f"Score global: {score:.1%}")
        
        return "; ".join(parts)
