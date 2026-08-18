"""
VisionEngine - Interface base para todos os motores de execução.

Motores são componentes especializados que executam tarefas pontuais
chamados pelos agentes. Cada motor tem uma responsabilidade única e
bem definida.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from enum import Enum
from uuid import UUID, uuid4
from datetime import datetime


class EngineStatus(str, Enum):
    """Status possíveis de um motor."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    MAINTENANCE = "maintenance"


class EngineCapability(str, Enum):
    """Capacidades que um motor pode declarar."""
    # Content
    IMAGE_GENERATION = "image_generation"
    CAPTION_GENERATION = "caption_generation"
    CAROUSEL_CREATION = "carousel_creation"
    REEL_SCRIPTING = "reel_scripting"
    CONTENT_PLANNING = "content_planning"
    
    # Analysis
    FACIAL_ANALYSIS = "facial_analysis"
    EXPRESSION_ANALYSIS = "expression_analysis"
    COLORIMETRY_ANALYSIS = "colorimetry_analysis"
    BODY_ANALYSIS = "body_analysis"
    
    # Casting
    CASTING_CLASSIFICATION = "casting_classification"
    CHARACTER_VARIATION = "character_variation"
    
    # Scheduling
    SCHEDULING = "scheduling"
    CALENDAR_INTEGRATION = "calendar_integration"
    
    # Publishing
    PUBLISHING = "publishing"
    METRICS_COLLECTION = "metrics_collection"
    
    # Communication
    WHATSAPP_MESSAGING = "whatsapp_messaging"
    EMAIL_SENDING = "email_sending"
    PUSH_NOTIFICATION = "push_notification"


class EngineResult:
    """Resultado padronizado da execução de um motor."""
    
    def __init__(
        self,
        success: bool,
        data: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        processing_time_ms: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.success = success
        self.data = data or {}
        self.error = error
        self.processing_time_ms = processing_time_ms
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "processing_time_ms": self.processing_time_ms,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }


class VisionEngine(ABC):
    """
    Interface base para todos os motores do Vision Ecosystem.
    
    Todo motor deve herdar desta classe e implementar:
    - execute: executa a tarefa específica
    - health_check: verifica a saúde do motor
    - get_capabilities: retorna as capacidades do motor
    """
    
    def __init__(
        self,
        engine_id: Optional[str] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        capabilities: Optional[List[EngineCapability]] = None,
    ):
        self.id = engine_id or str(uuid4())
        self.name = name or self.__class__.__name__
        self.description = description or ""
        self.capabilities = capabilities or []
        self.status = EngineStatus.HEALTHY
        self.created_at = datetime.utcnow()
        self.execution_count = 0
        self.error_count = 0
        self.total_processing_time_ms = 0
    
    @abstractmethod
    async def execute(self, task_data: Dict[str, Any]) -> EngineResult:
        """
        Executa uma tarefa específica.
        
        Args:
            task_data: Dados da tarefa a ser executada
            
        Returns:
            EngineResult com o resultado da execução
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """
        Verifica a saúde do motor.
        
        Returns:
            Dict com informações de saúde do motor
        """
        pass
    
    @abstractmethod
    def get_capabilities(self) -> List[EngineCapability]:
        """
        Retorna a lista de capacidades deste motor.
        
        Returns:
            Lista de EngineCapability
        """
        pass
    
    def has_capability(self, capability: EngineCapability) -> bool:
        """Verifica se o motor possui uma capacidade específica."""
        return capability in self.capabilities
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas de execução do motor."""
        avg_time = (
            self.total_processing_time_ms / max(self.execution_count, 1)
        )
        return {
            "engine_id": self.id,
            "name": self.name,
            "status": self.status.value,
            "capabilities": [c.value for c in self.capabilities],
            "execution_count": self.execution_count,
            "error_count": self.error_count,
            "error_rate": self.error_count / max(self.execution_count, 1),
            "avg_processing_time_ms": round(avg_time, 2),
            "total_processing_time_ms": self.total_processing_time_ms,
            "created_at": self.created_at.isoformat(),
        }
    
    def _record_execution(self, processing_time_ms: int, success: bool):
        """Registra uma execução."""
        self.execution_count += 1
        self.total_processing_time_ms += processing_time_ms
        if not success:
            self.error_count += 1
