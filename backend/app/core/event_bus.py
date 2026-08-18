"""
EventBus - Sistema de eventos do Vision Ecosystem.

Implementa arquitetura orientada a eventos para desacoplamento
total entre módulos. Qualquer componente pode emitir ou ouvir
eventos sem conhecer os outros.

Eventos suportados:
- USER_CREATED, PROFILE_UPDATED
- DIGITAL_TWIN_UPDATED
- CASTING_CREATED, CASTING_ANALYZED
- CONTENT_CREATED, CONTENT_APPROVAL_REQUESTED
- CONTENT_APPROVED, CONTENT_REJECTED, CONTENT_PUBLISHED
- METRICS_UPDATED
- AI_TASK_CREATED, AI_TASK_COMPLETED, AI_TASK_FAILED
"""

from typing import Dict, List, Any, Optional, Callable, Awaitable
from enum import Enum
from datetime import datetime
from uuid import uuid4
import asyncio
from dataclasses import dataclass, field

from app.utils.logger import get_logger

logger = get_logger(__name__)


class VisionEventType(str, Enum):
    """Tipos de eventos do sistema."""
    # User & Profile
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    PROFILE_UPDATED = "profile_updated"
    
    # Digital Twin
    DIGITAL_TWIN_UPDATED = "digital_twin_updated"
    DIGITAL_TWIN_ASSET_ADDED = "digital_twin_asset_added"
    
    # Casting
    CASTING_CREATED = "casting_created"
    CASTING_ANALYZED = "casting_analyzed"
    CASTING_MATCH_FOUND = "casting_match_found"
    CASTING_APPLICATION_SUBMITTED = "casting_application_submitted"
    
    # Content
    CONTENT_CREATED = "content_created"
    CONTENT_APPROVAL_REQUESTED = "content_approval_requested"
    CONTENT_APPROVED = "content_approved"
    CONTENT_REJECTED = "content_rejected"
    CONTENT_PUBLISHED = "content_published"
    CONTENT_SCHEDULED = "content_scheduled"
    
    # Metrics
    METRICS_UPDATED = "metrics_updated"
    ANALYTICS_READY = "analytics_ready"
    
    # AI Tasks
    AI_TASK_CREATED = "ai_task_created"
    AI_TASK_STARTED = "ai_task_started"
    AI_TASK_COMPLETED = "ai_task_completed"
    AI_TASK_FAILED = "ai_task_failed"
    AI_TASK_CANCELLED = "ai_task_cancelled"
    
    # Approval
    APPROVAL_PENDING = "approval_pending"
    APPROVAL_APPROVED = "approval_approved"
    APPROVAL_REJECTED = "approval_rejected"
    APPROVAL_REVISION_REQUESTED = "approval_revision_requested"
    
    # Workflow
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"
    
    # System
    SYSTEM_ERROR = "system_error"
    SYSTEM_WARNING = "system_warning"
    AUDIT_LOG_CREATED = "audit_log_created"


@dataclass
class VisionEvent:
    """Representa um evento no sistema."""
    event_type: VisionEventType
    payload: Dict[str, Any]
    event_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    source: Optional[str] = None
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    correlation_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "correlation_id": self.correlation_id,
        }


EventHandler = Callable[[VisionEvent], Awaitable[None]]


class EventBus:
    """
    Barramento de eventos do Vision Ecosystem.
    
    Permite:
    - Emitir eventos de forma assíncrona
    - Registrar handlers para tipos específicos de eventos
    - Registrar handlers globais (todos os eventos)
    - Persistir eventos para auditoria
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._handlers: Dict[VisionEventType, List[EventHandler]] = {}
        self._global_handlers: List[EventHandler] = []
        self._event_history: List[VisionEvent] = []
        self._max_history = 10000
        self._initialized = True
        self._lock = asyncio.Lock()
    
    def subscribe(
        self,
        event_type: VisionEventType,
        handler: EventHandler,
    ) -> None:
        """
        Registra um handler para um tipo específico de evento.
        
        Args:
            event_type: Tipo de evento a ouvir
            handler: Função assíncrona que será chamada
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        logger.debug(f"Handler registered for {event_type.value}")
    
    def subscribe_all(self, handler: EventHandler) -> None:
        """
        Registra um handler para TODOS os eventos.
        
        Args:
            handler: Função assíncrona que será chamada para todo evento
        """
        self._global_handlers.append(handler)
        logger.debug("Global handler registered")
    
    def unsubscribe(
        self,
        event_type: VisionEventType,
        handler: EventHandler,
    ) -> None:
        """Remove um handler de um tipo de evento."""
        if event_type in self._handlers:
            self._handlers[event_type] = [
                h for h in self._handlers[event_type] if h != handler
            ]
    
    async def emit(self, event: VisionEvent) -> None:
        """
        Emite um evento para todos os handlers registrados.
        
        Os handlers são executados de forma assíncrona e concorrente.
        Erros em handlers individuais não impedem a execução dos demais.
        
        Args:
            event: Evento a ser emitido
        """
        # Armazena no histórico
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history = self._event_history[-self._max_history:]
        
        logger.info(
            f"Event emitted: {event.event_type.value} "
            f"(id={event.event_id}, source={event.source})"
        )
        
        # Coleta todos os handlers a serem executados
        handlers: List[EventHandler] = []
        
        # Handers específicos do tipo
        if event.event_type in self._handlers:
            handlers.extend(self._handlers[event.event_type])
        
        # Handlers globais
        handlers.extend(self._global_handlers)
        
        # Executa todos de forma concorrente
        if handlers:
            await asyncio.gather(
                *[self._safe_execute(handler, event) for handler in handlers],
                return_exceptions=True,
            )
    
    async def _safe_execute(
        self,
        handler: EventHandler,
        event: VisionEvent,
    ) -> None:
        """Executa um handler com tratamento de erro."""
        try:
            await handler(event)
        except Exception as e:
            logger.error(
                f"Error in event handler for {event.event_type.value}: {e}",
                exc_info=True,
            )
    
    def get_history(
        self,
        event_type: Optional[VisionEventType] = None,
        limit: int = 100,
    ) -> List[VisionEvent]:
        """
        Retorna o histórico de eventos.
        
        Args:
            event_type: Filtrar por tipo específico
            limit: Número máximo de eventos
            
        Returns:
            Lista de eventos
        """
        events = self._event_history
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return events[-limit:]
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do event bus."""
        return {
            "total_events_emitted": len(self._event_history),
            "registered_event_types": len(self._handlers),
            "total_handlers": sum(len(h) for h in self._handlers.values()),
            "global_handlers": len(self._global_handlers),
            "event_type_counts": {
                et.value: len([e for e in self._event_history if e.event_type == et])
                for et in set(e.event_type for e in self._event_history)
            },
        }


# Instância global do event bus
event_bus = EventBus()


# Funções de conveniência
async def emit_event(
    event_type: VisionEventType,
    payload: Dict[str, Any],
    source: Optional[str] = None,
    user_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
) -> VisionEvent:
    """
    Função de conveniência para emitir eventos.
    
    Args:
        event_type: Tipo do evento
        payload: Dados do evento
        source: Componente que emitiu
        user_id: ID do usuário relacionado
        tenant_id: ID do tenant
        correlation_id: ID de correlação
        
    Returns:
        O evento criado
    """
    event = VisionEvent(
        event_type=event_type,
        payload=payload,
        source=source,
        user_id=user_id,
        tenant_id=tenant_id,
        correlation_id=correlation_id,
    )
    await event_bus.emit(event)
    return event
