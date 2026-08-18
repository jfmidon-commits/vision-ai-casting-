"""
backend/app/ai/visagism/multimodal_interpreter.py

Interpretador multimodal do VisagismAgent.

Usa um Foundation Model (GPT-4o) NAO para medir, mas para:
1. Interpretar qualitativamente o que as medicoes significam
2. Gerar justificativas personalizadas em linguagem natural
3. Validar consistencia entre medicoes e observacoes visuais
4. Preencher gaps onde a visao computacional e limitada

Principio: o LLM recebe as MEDICOES como contexto, nao adivinha.
"""

import json
import base64
from typing import Dict, List, Optional, Any
from uuid import UUID

import openai
from PIL import Image

from app.config import settings
from app.ai.visagism.schemas import EvidenceSource
from app.ai.visagism.evidence_tracker import EvidenceTracker


class VisagismMultimodalInterpreter:
    """
    Interpretador multimodal para visagismo.
    
    Recebe:
    - Fotos do protocolo
    - Medicoes e proporcoes do MeasurementEngine
    - Contexto do perfil
    
    Retorna:
    - Interpretacoes qualitativas validadas
    - Observacoes que complementam (nao substituem) as medicoes
    - Confidence explicito de que o LLM esta concordando com as medicoes
    """
    
    def __init__(self):
        self.client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4o"
        self.tracker: Optional[EvidenceTracker] = None
    
    async def interpret(
        self,
        photos: List[Dict[str, Any]],  # [{photo_id, image, angle, quality}]
        measurements: List[Dict[str, Any]],
        proportions: List[Dict[str, Any]],
        face_shape: str,
        profile_context: Dict[str, Any],
        tracker: EvidenceTracker,
    ) -> Dict[str, Any]:
        """
        Interpreta as medicoes e imagens via modelo multimodal.
        
        Returns:
            Dict com interpretacoes qualitativas e validacoes
        """
        self.tracker = tracker
        
        # Preparar contexto estruturado para o LLM
        context = self._build_context(measurements, proportions, face_shape, profile_context)
        
        # Selecionar fotos representativas (max 3 para economia)
        selected_photos = self._select_representative_photos(photos)
        
        # Construir mensagens
        messages = self._build_messages(context, selected_photos)
        
        # Chamar LLM
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.3,  # Baixa temperatura para consistencia
                max_tokens=2000,
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Validar contra medicoes
            validated = self._validate_against_measurements(result, measurements, proportions)
            
            # Registrar interpretacoes
            evidence_ids = []
            for interp in validated.get('interpretations', []):
                eid = tracker.register(
                    category="interpretation",
                    description=interp.get('description', ''),
                    value=interp,
                    source="llm_vision",
                    confidence=interp.get('confidence', 0.6),
                    raw_data={"llm_response": result, "validated": True},
                )
                evidence_ids.append(eid)
            
            return {
                "success": True,
                "interpretations": validated.get('interpretations', []),
                "validations": validated.get('validations', []),
                "qualitative_observations": validated.get('observations', []),
                "evidence_ids": evidence_ids,
                "confidence": validated.get('overall_confidence', 0.6),
            }
            
        except Exception as e:
            tracker.register(
                category="observation",
                description=f"Falha na interpretacao multimodal: {str(e)}",
                value=str(e),
                source="unknown",
                confidence=0.0,
            )
            return {
                "success": False,
                "error": str(e),
                "interpretations": [],
                "confidence": 0.0,
            }
    
    def _build_context(
        self,
        measurements: List[Dict[str, Any]],
        proportions: List[Dict[str, Any]],
        face_shape: str,
        profile_context: Dict[str, Any],
    ) -> str:
        """Constroi contexto estruturado das medicoes para o LLM."""
        
        lines = [
            "=== CONTEXTO DE MEDICOES FACIAIS ===",
            f"Formato facial classificado: {face_shape}",
            "",
            "=== MEDICOES (coordenadas normalizadas 0-1) ===",
        ]
        
        for m in measurements:
            lines.append(f"- {m['name']}: {m['value']:.4f} (confianca: {m.get('confidence', 'N/A')})")
        
        lines.extend(["", "=== PROPORCOES ==="])
        
        for p in proportions:
            ideal = p.get('ideal_range', ('?', '?'))
            lines.append(
                f"- {p['name']}: {p['value']:.3f} "
                f"(ideal: {ideal[0]}-{ideal[1]}, "
                f"classificacao: {p.get('classification', 'N/A')})"
            )
        
        lines.extend(["", "=== PERFIL ==="])
        lines.append(f"Genero: {profile_context.get('gender', 'N/A')}")
        lines.append(f"Idade estimada: {profile_context.get('age_estimate', 'N/A')}")
        lines.append(f"Cabelo atual: {profile_context.get('current_hair_length', 'N/A')}")
        
        return "\n".join(lines)
    
    def _select_representative_photos(
        self,
        photos: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Seleciona ate 3 fotos representativas."""
        priority = ['front_neutral', 'profile_right', 'three_quarter_right']
        selected = []
        
        for p in priority:
            for photo in photos:
                if photo.get('angle') == p and photo.get('is_usable', True):
                    selected.append(photo)
                    break
            if len(selected) >= 3:
                break
        
        # Se nao encontrou prioridades, pega as primeiras usaveis
        if not selected:
            selected = [p for p in photos if p.get('is_usable', True)][:3]
        
        return selected
    
    def _build_messages(
        self,
        context: str,
        photos: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Constroi mensagens para o LLM multimodal."""
        
        system_prompt = """Voce e um consultor senior de visagismo capilar.

REGRAS ABSOLUTAS:
1. Voce NAO mede — as medicoes ja foram feitas por sistema de visao computacional.
2. Voce INTERPRETA o que as medicoes significam visualmente.
3. Voce VALIDA se suas observacoes sao consistentes com as medicoes.
4. Voce NUNCA contradiz uma medicao numerica sem explicar o porque.
5. Voce NAO infere personalidade, carater, saude ou origem etnica.
6. Voce fala apenas de ANALISE VISUAL e DIRECAO DE IMAGEM.

Sua tarefa:
- Dado o contexto de medicoes e as imagens, forneca interpretacoes qualitativas
- Identifique pontos fortes visuais
- Sugira aspectos que podem ser modificados ou preservados
- Valide se o formato facial classificado faz sentido visualmente

Responda em JSON com esta estrutura:
{
  "interpretations": [
    {
      "aspect": "nome do aspecto",
      "description": "descricao qualitativa",
      "confidence": 0.0-1.0,
      "agrees_with_measurement": true/false,
      "measurement_reference": "nome_da_medicao"
    }
  ],
  "validations": [
    {
      "claim": "afirmacao validada",
      "measurement_support": "medicao que suporta",
      "is_consistent": true/false
    }
  ],
  "observations": [
    {
      "region": "regiao facial",
      "observation": "observacao qualitativa",
      "visual_impact": "impacto visual"
    }
  ],
  "overall_confidence": 0.0-1.0
}"""
        
        # Conteudo da mensagem do usuario
        content = [{"type": "text", "text": context}]
        
        # Adicionar imagens
        for photo in photos:
            image = photo.get('image')
            if image and hasattr(image, 'convert'):
                # Converter para base64
                import io
                buffer = io.BytesIO()
                image.convert('RGB').save(buffer, format='JPEG', quality=85)
                img_b64 = base64.b64encode(buffer.getvalue()).decode()
                
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{img_b64}",
                        "detail": "low",  # Baixo detalhe para economia
                    }
                })
        
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content},
        ]
    
    def _validate_against_measurements(
        self,
        llm_result: Dict[str, Any],
        measurements: List[Dict[str, Any]],
        proportions: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Valida interpretacoes do LLM contra medicoes concretas."""
        
        m_dict = {m['name']: m for m in measurements}
        p_dict = {p['name']: p for p in proportions}
        
        validations = []
        
        for interp in llm_result.get('interpretations', []):
            ref = interp.get('measurement_reference', '')
            
            if ref in m_dict or ref in p_dict:
                # Verificar consistencia
                measurement = m_dict.get(ref) or p_dict.get(ref)
                interp_value = interp.get('confidence', 0.5)
                meas_confidence = measurement.get('confidence', 0.5)
                
                # Se LLM discorda de medicao de alta confianca, reduzir confianca da interpretacao
                if not interp.get('agrees_with_measurement', True) and meas_confidence > 0.8:
                    interp['confidence'] = min(interp_value, 0.4)
                    interp['warning'] = "Discorda de medicao de alta confianca"
                
                validations.append({
                    "claim": interp.get('description', ''),
                    "measurement_support": ref,
                    "is_consistent": interp.get('agrees_with_measurement', True),
                    "measurement_confidence": meas_confidence,
                })
        
        llm_result['validations'] = validations
        
        # Calcular confidence geral baseado em consistencia
        if validations:
            consistency = sum(1 for v in validations if v['is_consistent']) / len(validations)
            llm_result['overall_confidence'] = round(consistency * 0.8, 3)  # Max 0.8 para LLM
        else:
            llm_result['overall_confidence'] = 0.5
        
        return llm_result
