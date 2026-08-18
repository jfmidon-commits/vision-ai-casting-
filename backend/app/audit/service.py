"""
AuditService - Serviço de Logs de Auditoria.

Responsável por:
- Registrar todas as ações importantes do sistema
- Manter histórico de alterações (before/after)
- Suportar compliance e investigação
"""

from typing import Dict, Any, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog
from app.core.event_bus import emit_event, VisionEventType
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AuditService:
    """Serviço de Logs de Auditoria."""

    async def log_action(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        action: str,
        entity_type: str,
        entity_id: Optional[str] = None,
        user_id: Optional[UUID] = None,
        agent_name: Optional[str] = None,
        before_state: Optional[Dict] = None,
        after_state: Optional[Dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> AuditLog:
        """Registra uma ação no audit log."""
        log = AuditLog(
            tenant_id=tenant_id,
            user_id=user_id,
            agent_name=agent_name,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            before_state=before_state,
            after_state=after_state,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata or {},
        )

        db.add(log)
        await db.commit()
        await db.refresh(log)

        await emit_event(
            event_type=VisionEventType.AUDIT_LOG_CREATED,
            payload={
                "log_id": str(log.id),
                "action": action,
                "entity_type": entity_type,
            },
        )

        return log

    async def log_agent_execution(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
        agent_name: str,
        intent: str,
        result: Dict[str, Any],
    ) -> AuditLog:
        """Registra a execução de um agente."""
        return await self.log_action(
            db=db,
            tenant_id=tenant_id,
            user_id=user_id,
            agent_name=agent_name,
            action="AGENT_EXECUTION",
            entity_type="AI_TASK",
            after_state={
                "intent": intent,
                "result": result,
            },
        )
