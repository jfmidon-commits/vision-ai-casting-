"""
VisionAgent - Interface base para todos os mini-cérebros do Vision Ecosystem.

Todo agente especializado deve herdar desta classe e implementar os métodos
obrigatórios. O Vision Core usa essa interface para orquestrar tarefas sem
conhecer detalhes internos de cada agente.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from enum import Enum
from uuid import UUID, uuid4
from datetime import datetime


class AgentStatus(str, Enum):
    """Status possíveis de um agente."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    ERROR = "error"


class AgentCapability(str, Enum):
    """Capacidades que um agente pode declarar."""
    # Identity
    PROFILE_MANAGEMENT = "profile_management"
    IDENTITY_VERIFICATION = "identity_verification"
    
    # Visagism
    VISAGISM_ANALYSIS = "visagism_analysis"
    STYLE_RECOMMENDATION = "style_recommendation"
    
    # Digital Twin
    DIGITAL_TWIN_CREATION = "digital_twin_creation"
    DIGITAL_TWIN_UPDATE = "digital_twin_update"
    CHARACTER_SIMULATION = "character_simulation"
    
    # Casting
    CASTING_ANALYSIS = "casting_analysis"
    CASTING_MATCHING = "casting_matching"
    CASTING_APPLICATION = "casting_application"
    
    # Portfolio
    PORTFOLIO_MANAGEMENT = "portfolio_management"
    PORTFOLIO_OPTIMIZATION = "portfolio_optimization"
    
    # Social
    CONTENT_CREATION = "content_creation"
    CONTENT_SCHEDULING = "content_scheduling"
    SOCIAL_PUBLISHING = "social_publishing"
    
    # Opportunities
    OPPORTUNITY_SEARCH = "opportunity_search"
    OPPORTUNITY_MATCHING = "opportunity_matching"
    
    # Approval
    APPROVAL_WORKFLOW = "approval_workflow"
    HUMAN_REVIEW = "human_review"
    
    # Analytics
    PERFORMANCE_ANALYSIS = "performance_analysis"
    METRICS_COLLECTION = "metrics_collection"
    
    # Automation
    WORKFLOW_AUTOMATION = "workflow_automation"
    COMMUNICATION_AUTOMATION = "communication_automation"


class AgentContext:
    """Contexto passado para um agente durante a execução."""
    
    def __init__(
        self,
        user_id: UUID,
        tenant_id: UUID,
        intent: str,
        input_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
        memory: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ):
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.intent = intent
        self.input_data = input_data
        self.metadata = metadata or {}
        self.memory = memory or {}
        self.session_id = session_id or str(uuid4())
        self.created_at = datetime.utcnow()
        self.agent_results: Dict[str, Any] = {}
    
    def add_result(self, key: str, value: Any):
        """Adiciona um resultado ao contexto."""
        self.agent_results[key] = value
    
    def get_result(self, key: str) -> Optional[Any]:
        """Recupera um resultado do contexto."""
        return self.agent_results.get(key)


class AgentResult:
    """Resultado padronizado da execução de um agente."""
    
    def __init__(
        self,
        success: bool,
        data: Optional[Dict[str, Any]] = None,
        message: Optional[str] = None,
        error: Optional[str] = None,
        requires_approval: bool = False,
        approval_type: Optional[str] = None,
        confidence: float = 1.0,
    ):
        self.success = success
        self.data = data or {}
        self.message = message
        self.error = error
        self.requires_approval = requires_approval
        self.approval_type = approval_type
        self.confidence = confidence
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "message": self.message,
            "error": self.error,
            "requires_approval": self.requires_approval,
            "approval_type": self.approval_type,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
        }


class VisionAgent(ABC):
    """
    Interface base para todos os agentes do Vision Ecosystem.
    
    Todo mini-cérebro deve herdar desta classe e implementar:
    - can_handle: determina se o agente pode processar uma intenção
    - execute: executa a tarefa e retorna um AgentResult
    - validate: valida o resultado da execução
    """
    
    def __init__(
        self,
        agent_id: Optional[str] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        capabilities: Optional[List[AgentCapability]] = None,
    ):
        self.id = agent_id or str(uuid4())
        self.name = name or self.__class__.__name__
        self.description = description or ""
        self.capabilities = capabilities or []
        self.status = AgentStatus.ACTIVE
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.execution_count = 0
        self.error_count = 0
    
    @abstractmethod
    def can_handle(self, context: AgentContext) -> bool:
        """
        Determina se este agente pode processar a intenção do contexto.
        
        Args:
            context: O contexto de execução contendo a intenção
            
        Returns:
            True se o agente pode processar, False caso contrário
        """
        pass
    
    @abstractmethod
    async def execute(self, context: AgentContext) -> AgentResult:
        """
        Executa a tarefa associada ao contexto.
        
        Args:
            context: O contexto de execução completo
            
        Returns:
            AgentResult com o resultado da execução
        """
        pass
    
    @abstractmethod
    def validate(self, result: AgentResult) -> bool:
        """
        Valida se o resultado da execução é aceitável.
        
        Args:
            result: O resultado a ser validado
            
        Returns:
            True se o resultado é válido, False caso contrário
        """
        pass
    
    def get_capabilities(self) -> List[AgentCapability]:
        """Retorna a lista de capacidades deste agente."""
        return self.capabilities.copy()
    
    def has_capability(self, capability: AgentCapability) -> bool:
        """Verifica se o agente possui uma capacidade específica."""
        return capability in self.capabilities
    
    def health_check(self) -> Dict[str, Any]:
        """Retorna o status de saúde do agente."""
        return {
            "agent_id": self.id,
            "name": self.name,
            "status": self.status.value,
            "capabilities": [c.value for c in self.capabilities],
            "execution_count": self.execution_count,
            "error_count": self.error_count,
            "error_rate": self.error_count / max(self.execution_count, 1),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
    
    def _increment_execution(self):
        """Incrementa o contador de execuções."""
        self.execution_count += 1
        self.updated_at = datetime.utcnow()
    
    def _increment_error(self):
        """Incrementa o contador de erros."""
        self.error_count += 1
        self.updated_at = datetime.utcnow()
