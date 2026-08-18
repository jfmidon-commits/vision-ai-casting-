"""
IntentRecognizer - Reconhecedor de intenções do Vision Core.

Converte texto/voz do usuário em intenções estruturadas.
Na versão atual usa mapeamento simples por palavras-chave.
Futuramente usará LLM para NLP avançado.
"""

from typing import Dict, Any, Optional
from enum import Enum
from app.utils.logger import get_logger

logger = get_logger(__name__)


class IntentType(str, Enum):
    CREATE_CONTENT = "CREATE_CONTENT"
    ANALYZE_CASTING = "ANALYZE_CASTING"
    GENERATE_CHARACTER = "GENERATE_CHARACTER"
    UPDATE_PROFILE = "UPDATE_PROFILE"
    SEARCH_OPPORTUNITIES = "SEARCH_OPPORTUNITIES"
    PREPARE_APPLICATION = "PREPARE_APPLICATION"
    ANALYZE_VISAGISM = "ANALYZE_VISAGISM"
    SCHEDULE_CONTENT = "SCHEDULE_CONTENT"
    PUBLISH_CONTENT = "PUBLISH_CONTENT"
    REQUEST_APPROVAL = "REQUEST_APPROVAL"
    AUTOMATE_WORKFLOW = "AUTOMATE_WORKFLOW"
    UNKNOWN = "UNKNOWN"


class IntentRecognizer:
    """
    Reconhecedor de intenções do Vision Core.

    Converte texto/voz do usuário em intenções estruturadas.
    Na versão atual usa mapeamento simples por palavras-chave.
    Futuramente usará LLM para NLP avançado.
    """

    KEYWORD_MAP = {
        "postagem": IntentType.CREATE_CONTENT,
        "post": IntentType.CREATE_CONTENT,
        "conteudo": IntentType.CREATE_CONTENT,
        "legenda": IntentType.CREATE_CONTENT,
        "carrossel": IntentType.CREATE_CONTENT,
        "reel": IntentType.CREATE_CONTENT,
        "casting": IntentType.ANALYZE_CASTING,
        "personagem": IntentType.GENERATE_CHARACTER,
        "perfil": IntentType.UPDATE_PROFILE,
        "oportunidade": IntentType.SEARCH_OPPORTUNITIES,
        "vaga": IntentType.SEARCH_OPPORTUNITIES,
        "candidatura": IntentType.PREPARE_APPLICATION,
        "visagismo": IntentType.ANALYZE_VISAGISM,
        "agendar": IntentType.SCHEDULE_CONTENT,
        "publicar": IntentType.PUBLISH_CONTENT,
        "aprovar": IntentType.REQUEST_APPROVAL,
        "automatizar": IntentType.AUTOMATE_WORKFLOW,
    }

    def recognize(self, text: str) -> IntentType:
        """
        Reconhece a intenção a partir do texto do usuário.

        Args:
            text: Texto do comando do usuário

        Returns:
            IntentType identificado
        """
        text_lower = text.lower()

        for keyword, intent in self.KEYWORD_MAP.items():
            if keyword in text_lower:
                logger.info(f"Intent recognized: {intent.value} (keyword: {keyword})")
                return intent

        logger.info(f"Intent not recognized, defaulting to UNKNOWN")
        return IntentType.UNKNOWN

    def recognize_with_confidence(self, text: str) -> Dict[str, Any]:
        """
        Reconhece intenção com score de confiança.

        Returns:
            Dict com intent e confidence
        """
        intent = self.recognize(text)
        confidence = 0.9 if intent != IntentType.UNKNOWN else 0.0

        return {
            "intent": intent.value,
            "confidence": confidence,
            "raw_text": text,
        }
