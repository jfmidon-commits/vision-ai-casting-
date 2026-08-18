"""
AITaskService - Gerenciador de Tarefas de IA.

Responsável por:
- Criar e rastrear tarefas de IA
- Gerenciar estados (PENDING, PROCESSING, WAITING_APPROVAL, COMPLETED, FAILED, CANCELLED)
- Registrar métricas de execução
- Integrar com o Event Bus
"""

from typing import Dict, List, Any, Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models import AITask
from app.core.event_bus import emit_event, VisionEventType
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AITaskService:
    """Gerenciador de Tarefas de IA."""

    async def create_task(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
        task_type: str,
        input_data: Dict[str, Any],
        agent_name: Optional[str] = None,
        engine_name: Optional[str] = None,
        provider_name: Optional[str] = None,
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> AITask:
        """Cria uma nova tarefa de IA."""
        task = AITask(
            tenant_id=tenant_id,
            user_id=user_id,
            task_type=task_type,
            input_data=input_data,
            status="pending",
            agent_name=agent_name,
            engine_name=engine_name,
            provider_name=provider_name,
            correlation_id=correlation_id,
            metadata=metadata or {},
        )

        db.add(task)
        await db.commit()
        await db.refresh(task)

        await emit_event(
            event_type=VisionEventType.AI_TASK_CREATED,
            payload={
                "task_id": str(task.id),
                "task_type": task_type,
                "agent": agent_name,
            },
        )

        logger.info(f"AI Task created: {task.id}")
        return task

    async def start_task(
        self,
        db: AsyncSession,
        task_id: UUID,
        tenant_id: UUID,
    ) -> Optional[AITask]:
        """Marca uma tarefa como em processamento."""
        task = await self._get_task(db, task_id, tenant_id)
        if not task:
            return None

        task.status = "processing"
        task.started_at = datetime.utcnow()
        await db.commit()

        await emit_event(
            event_type=VisionEventType.AI_TASK_STARTED,
            payload={"task_id": str(task_id)},
        )

        return task

    async def complete_task(
        self,
        db: AsyncSession,
        task_id: UUID,
        tenant_id: UUID,
        output_data: Dict[str, Any],
        processing_time_ms: int,
    ) -> Optional[AITask]:
        """Marca uma tarefa como completada."""
        task = await self._get_task(db, task_id, tenant_id)
        if not task:
            return None

        task.status = "completed"
        task.output_data = output_data
        task.processing_time_ms = processing_time_ms
        task.completed_at = datetime.utcnow()
        await db.commit()

        await emit_event(
            event_type=VisionEventType.AI_TASK_COMPLETED,
            payload={
                "task_id": str(task_id),
                "processing_time_ms": processing_time_ms,
            },
        )

        return task

    async def fail_task(
        self,
        db: AsyncSession,
        task_id: UUID,
        tenant_id: UUID,
        error_message: str,
    ) -> Optional[AITask]:
        """Marca uma tarefa como falha."""
        task = await self._get_task(db, task_id, tenant_id)
        if not task:
            return None

        task.status = "failed"
        task.error_message = error_message
        task.completed_at = datetime.utcnow()
        await db.commit()

        await emit_event(
            event_type=VisionEventType.AI_TASK_FAILED,
            payload={
                "task_id": str(task_id),
                "error": error_message,
            },
        )

        return task

    async def _get_task(
        self,
        db: AsyncSession,
        task_id: UUID,
        tenant_id: UUID,
    ) -> Optional[AITask]:
        """Busca uma tarefa por ID."""
        result = await db.execute(
            select(AITask).where(
                and_(
                    AITask.id == task_id,
                    AITask.tenant_id == tenant_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def list_tasks(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        user_id: Optional[UUID] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[AITask]:
        """Lista tarefas com filtros."""
        query = select(AITask).where(AITask.tenant_id == tenant_id)

        if user_id:
            query = query.where(AITask.user_id == user_id)
        if status:
            query = query.where(AITask.status == status)

        query = query.order_by(AITask.created_at.desc()).limit(limit)

        result = await db.execute(query)
        return result.scalars().all()
