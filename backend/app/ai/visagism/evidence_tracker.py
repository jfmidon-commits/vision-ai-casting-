"""
backend/app/ai/visagism/evidence_tracker.py

Sistema de rastreabilidade de evidencias do VisagismAgent.

Garante que cada conclusao do sistema possa ser rastreada ate as
evidenencias que a fundamentam, implementando o principio:

    OBSERVADO -> MEDIDO -> INTERPRETADO -> RECOMENDADO

Cada evidencia recebe um ID unico. Cada conclusao registra quais
evidenencias a suportam. O evidence_map no resultado final permite
auditar qualquer decisao do sistema.
"""

import uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class Evidence:
    """Uma evidencia observada ou medida."""
    evidence_id: str
    category: str  # "measurement", "proportion", "observation", "inference"
    description: str
    value: Any
    source: str
    confidence: float
    photo_id: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None
    derived_from: List[str] = field(default_factory=list)  # IDs de evidencias pai


class EvidenceTracker:
    """
    Rastreador de evidencias para o pipeline de visagismo.
    
    Responsavel por:
    - Gerar IDs unicos para cada evidencia
    - Registrar a cadeia de derivacao (evidencia A -> proporcao B -> interpretacao C)
    - Permitir auditoria reversa: dada uma conclusao, encontrar suas evidencias
    - Calcular confidence agregado a partir das evidencias de base
    """
    
    def __init__(self):
        self._evidences: Dict[str, Evidence] = {}
        self._conclusion_map: Dict[str, List[str]] = {}  # conclusao -> [evidence_ids]
    
    def register(
        self,
        category: str,
        description: str,
        value: Any,
        source: str,
        confidence: float,
        photo_id: Optional[str] = None,
        raw_data: Optional[Dict[str, Any]] = None,
        derived_from: Optional[List[str]] = None,
    ) -> str:
        """
        Registra uma nova evidencia e retorna seu ID.
        
        Args:
            category: Tipo de evidencia (measurement, proportion, observation, inference)
            description: Descricao legivel da evidencia
            value: Valor da evidencia (numero, string, dict, etc)
            source: Fonte (mediapipe_landmark, computed_ratio, llm_vision, etc)
            confidence: Confidencia 0-1
            photo_id: ID da foto relacionada, se houver
            raw_data: Dados brutos para auditoria
            derived_from: IDs de evidencias das quais esta deriva
            
        Returns:
            ID unico da evidencia registrada
        """
        evidence_id = f"{category}_{uuid.uuid4().hex[:12]}"
        
        evidence = Evidence(
            evidence_id=evidence_id,
            category=category,
            description=description,
            value=value,
            source=source,
            confidence=confidence,
            photo_id=str(photo_id) if photo_id else None,
            raw_data=raw_data,
            derived_from=derived_from or [],
        )
        
        self._evidences[evidence_id] = evidence
        return evidence_id
    
    def link_conclusion(
        self,
        conclusion_key: str,
        evidence_ids: List[str],
    ) -> None:
        """
        Liga uma conclusao as evidencias que a fundamentam.
        
        Args:
            conclusion_key: Identificador da conclusao (ex: "face_shape_oblong")
            evidence_ids: Lista de IDs de evidencias
        """
        if conclusion_key not in self._conclusion_map:
            self._conclusion_map[conclusion_key] = []
        
        for eid in evidence_ids:
            if eid not in self._conclusion_map[conclusion_key]:
                self._conclusion_map[conclusion_key].append(eid)
    
    def get_evidence(self, evidence_id: str) -> Optional[Evidence]:
        """Recupera uma evidencia pelo ID."""
        return self._evidences.get(evidence_id)
    
    def get_evidences_for_conclusion(self, conclusion_key: str) -> List[Evidence]:
        """Recupera todas as evidencias que fundamentam uma conclusao."""
        evidence_ids = self._conclusion_map.get(conclusion_key, [])
        return [self._evidences[eid] for eid in evidence_ids if eid in self._evidences]
    
    def get_confidence_for_conclusion(self, conclusion_key: str) -> float:
        """
        Calcula o confidence agregado de uma conclusao.
        
        Usa a media geometrica dos confidences das evidencias de base,
        penalizando conclusoes com pouca evidencia.
        """
        evidences = self.get_evidences_for_conclusion(conclusion_key)
        if not evidences:
            return 0.0
        
        confidences = [e.confidence for e in evidences]
        
        # Media geometrica
        product = 1.0
        for c in confidences:
            product *= c
        geometric_mean = product ** (1.0 / len(confidences))
        
        # Penalidade por pouca evidencia
        evidence_penalty = min(1.0, len(evidences) / 3.0)
        
        return round(geometric_mean * evidence_penalty, 3)
    
    def get_evidence_map(self) -> Dict[str, List[str]]:
        """Retorna o mapa completo de conclusao -> evidencias."""
        return dict(self._conclusion_map)
    
    def get_all_evidences(self) -> List[Evidence]:
        """Retorna todas as evidencias registradas."""
        return list(self._evidences.values())
    
    def get_evidence_chain(self, evidence_id: str) -> List[Evidence]:
        """
        Retorna a cadeia completa de derivacao de uma evidencia.
        
        Ex: se evidencia C deriva de B, que deriva de A,
        retorna [C, B, A].
        """
        chain = []
        current_id = evidence_id
        visited = set()
        
        while current_id and current_id not in visited:
            visited.add(current_id)
            evidence = self._evidences.get(current_id)
            if evidence:
                chain.append(evidence)
                # Segue a primeira evidencia pai (arvore de derivacao)
                if evidence.derived_from:
                    current_id = evidence.derived_from[0]
                else:
                    break
            else:
                break
        
        return chain
    
    def audit_conclusion(self, conclusion_key: str) -> Dict[str, Any]:
        """
        Gera um relatorio de auditoria completo para uma conclusao.
        
        Retorna a conclusao, suas evidencias, a cadeia de derivacao
        de cada evidencia, e o calculo de confidence.
        """
        evidences = self.get_evidences_for_conclusion(conclusion_key)
        
        audit = {
            "conclusion": conclusion_key,
            "confidence": self.get_confidence_for_conclusion(conclusion_key),
            "evidence_count": len(evidences),
            "evidences": [],
        }
        
        for evidence in evidences:
            chain = self.get_evidence_chain(evidence.evidence_id)
            audit["evidences"].append({
                "evidence_id": evidence.evidence_id,
                "category": evidence.category,
                "description": evidence.description,
                "value": evidence.value,
                "source": evidence.source,
                "confidence": evidence.confidence,
                "photo_id": evidence.photo_id,
                "derivation_chain": [
                    {"id": e.evidence_id, "description": e.description, "source": e.source}
                    for e in chain
                ],
            })
        
        return audit
