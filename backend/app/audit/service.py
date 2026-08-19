"""
AuditService - Serviço de Logs de Auditoria Completo.

Responsável por:
- Registrar todas as ações importantes do sistema
- Manter histórico de alterações (before/after)
- Suportar compliance e investigação
- Busca e filtragem de logs
- Exportação de relatórios de auditoria
"""

from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.dialects.postgresql import insert

from app.models import AuditLog
from app.core.event_bus import emit_event, VisionEventType
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AuditService:
    """Serviço de Logs de Auditoria com persistência completa."""

    def __init__(self):
        self._batch_buffer: List[Dict[str, Any]] = []
        self._batch_size = 100

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
        severity: str = "info",  # info, warning, error, critical
    ) -> AuditLog:
        """
        Registra uma ação no audit log.

        Args:
            db: Sessão do banco de dados
            tenant_id: ID do tenant
            action: Nome da ação (ex: "USER_LOGIN", "PROFILE_UPDATE")
            entity_type: Tipo da entidade (ex: "user", "profile", "analysis")
            entity_id: ID da entidade afetada
            user_id: ID do usuário que executou a ação
            agent_name: Nome do agente (se ação foi por agente)
            before_state: Estado antes da alteração
            after_state: Estado após a alteração
            ip_address: IP do usuário
            user_agent: User agent do navegador
            metadata: Metadados adicionais
            severity: Severidade do log

        Returns:
            AuditLog: Registro criado
        """
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
            severity=severity,
            metadata=metadata or {},
        )

        db.add(log)
        await db.commit()
        await db.refresh(log)

        # Emitir evento para notificações em tempo real
        await emit_event(
            event_type=VisionEventType.AUDIT_LOG_CREATED,
            payload={
                "log_id": str(log.id),
                "action": action,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "severity": severity,
                "tenant_id": str(tenant_id),
            },
        )

        logger.info(f"Audit log created: {action} on {entity_type}:{entity_id}")
        return log

    async def log_agent_execution(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
        agent_name: str,
        intent: str,
        result: Dict[str, Any],
        input_data: Optional[Dict] = None,
        processing_time_ms: Optional[int] = None,
        model_version: Optional[str] = None,
    ) -> AuditLog:
        """
        Registra a execução de um agente.

        Args:
            db: Sessão do banco de dados
            tenant_id: ID do tenant
            user_id: ID do usuário
            agent_name: Nome do agente executado
            intent: Intenção detectada
            result: Resultado da execução
            input_data: Dados de entrada
            processing_time_ms: Tempo de processamento em ms
            model_version: Versão do modelo usado

        Returns:
            AuditLog: Registro criado
        """
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
                "input_data": input_data,
                "processing_time_ms": processing_time_ms,
                "model_version": model_version,
            },
            metadata={
                "agent_name": agent_name,
                "intent": intent,
                "processing_time_ms": processing_time_ms,
                "model_version": model_version,
            },
        )

    async def log_user_action(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
        action: str,
        entity_type: str,
        entity_id: Optional[str] = None,
        before_state: Optional[Dict] = None,
        after_state: Optional[Dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """
        Registra uma ação do usuário.

        Args:
            db: Sessão do banco de dados
            tenant_id: ID do tenant
            user_id: ID do usuário
            action: Nome da ação
            entity_type: Tipo da entidade
            entity_id: ID da entidade
            before_state: Estado anterior
            after_state: Estado posterior
            ip_address: IP do usuário
            user_agent: User agent

        Returns:
            AuditLog: Registro criado
        """
        return await self.log_action(
            db=db,
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            before_state=before_state,
            after_state=after_state,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def log_security_event(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        action: str,
        severity: str,
        user_id: Optional[UUID] = None,
        ip_address: Optional[str] = None,
        details: Optional[Dict] = None,
    ) -> AuditLog:
        """
        Registra um evento de segurança.

        Args:
            db: Sessão do banco de dados
            tenant_id: ID do tenant
            action: Nome do evento (ex: "FAILED_LOGIN", "SUSPICIOUS_ACTIVITY")
            severity: Severidade (warning, error, critical)
            user_id: ID do usuário (se aplicável)
            ip_address: IP associado
            details: Detalhes do evento

        Returns:
            AuditLog: Registro criado
        """
        return await self.log_action(
            db=db,
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            entity_type="SECURITY_EVENT",
            severity=severity,
            ip_address=ip_address,
            metadata=details or {},
        )

    async def log_data_change(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
        entity_type: str,
        entity_id: str,
        before_state: Dict,
        after_state: Dict,
        change_description: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """
        Registra uma alteração de dados com diff completo.

        Args:
            db: Sessão do banco de dados
            tenant_id: ID do tenant
            user_id: ID do usuário
            entity_type: Tipo da entidade
            entity_id: ID da entidade
            before_state: Estado completo antes
            after_state: Estado completo depois
            change_description: Descrição da mudança
            ip_address: IP do usuário

        Returns:
            AuditLog: Registro criado
        """
        # Calcular diff
        diff = self._calculate_diff(before_state, after_state)

        return await self.log_action(
            db=db,
            tenant_id=tenant_id,
            user_id=user_id,
            action="DATA_CHANGE",
            entity_type=entity_type,
            entity_id=entity_id,
            before_state=before_state,
            after_state=after_state,
            ip_address=ip_address,
            metadata={
                "diff": diff,
                "change_description": change_description,
                "changed_fields": list(diff.keys()),
            },
        )

    def _calculate_diff(self, before: Dict, after: Dict) -> Dict[str, Any]:
        """Calcula diff entre dois estados."""
        diff = {}
        all_keys = set(before.keys()) | set(after.keys())

        for key in all_keys:
            before_val = before.get(key)
            after_val = after.get(key)

            if before_val != after_val:
                diff[key] = {
                    "before": before_val,
                    "after": after_val,
                }

        return diff

    # ========== CONSULTAS ==========

    async def get_logs(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        action: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        user_id: Optional[UUID] = None,
        agent_name: Optional[str] = None,
        severity: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        Busca logs de auditoria com filtros.

        Args:
            db: Sessão do banco de dados
            tenant_id: ID do tenant
            action: Filtrar por ação
            entity_type: Filtrar por tipo de entidade
            entity_id: Filtrar por ID de entidade
            user_id: Filtrar por usuário
            agent_name: Filtrar por agente
            severity: Filtrar por severidade
            start_date: Data inicial
            end_date: Data final
            limit: Limite de resultados
            offset: Offset para paginação

        Returns:
            Dict com logs e metadados de paginação
        """
        query = select(AuditLog).where(AuditLog.tenant_id == tenant_id)

        if action:
            query = query.where(AuditLog.action == action)
        if entity_type:
            query = query.where(AuditLog.entity_type == entity_type)
        if entity_id:
            query = query.where(AuditLog.entity_id == entity_id)
        if user_id:
            query = query.where(AuditLog.user_id == user_id)
        if agent_name:
            query = query.where(AuditLog.agent_name == agent_name)
        if severity:
            query = query.where(AuditLog.severity == severity)
        if start_date:
            query = query.where(AuditLog.created_at >= start_date)
        if end_date:
            query = query.where(AuditLog.created_at <= end_date)

        # Contar total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()

        # Ordenar e paginar
        query = query.order_by(desc(AuditLog.created_at)).offset(offset).limit(limit)

        result = await db.execute(query)
        logs = result.scalars().all()

        return {
            "logs": [
                {
                    "id": str(log.id),
                    "action": log.action,
                    "entity_type": log.entity_type,
                    "entity_id": log.entity_id,
                    "user_id": str(log.user_id) if log.user_id else None,
                    "agent_name": log.agent_name,
                    "severity": log.severity,
                    "ip_address": log.ip_address,
                    "before_state": log.before_state,
                    "after_state": log.after_state,
                    "metadata": log.metadata,
                    "created_at": (
                        log.created_at.isoformat() if log.created_at else None
                    ),
                }
                for log in logs
            ],
            "pagination": {
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": offset + len(logs) < total,
            },
        }

    async def get_entity_history(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        entity_type: str,
        entity_id: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Recupera histórico completo de uma entidade.

        Args:
            db: Sessão do banco de dados
            tenant_id: ID do tenant
            entity_type: Tipo da entidade
            entity_id: ID da entidade
            limit: Limite de resultados

        Returns:
            Lista de alterações da entidade
        """
        result = await db.execute(
            select(AuditLog)
            .where(
                and_(
                    AuditLog.tenant_id == tenant_id,
                    AuditLog.entity_type == entity_type,
                    AuditLog.entity_id == entity_id,
                )
            )
            .order_by(desc(AuditLog.created_at))
            .limit(limit)
        )
        logs = result.scalars().all()

        return [
            {
                "id": str(log.id),
                "action": log.action,
                "user_id": str(log.user_id) if log.user_id else None,
                "agent_name": log.agent_name,
                "before_state": log.before_state,
                "after_state": log.after_state,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ]

    async def get_user_activity(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """
        Recupera atividade de um usuário.

        Args:
            db: Sessão do banco de dados
            tenant_id: ID do tenant
            user_id: ID do usuário
            start_date: Data inicial
            end_date: Data final
            limit: Limite de resultados

        Returns:
            Dict com atividade do usuário
        """
        query = select(AuditLog).where(
            and_(
                AuditLog.tenant_id == tenant_id,
                AuditLog.user_id == user_id,
            )
        )

        if start_date:
            query = query.where(AuditLog.created_at >= start_date)
        if end_date:
            query = query.where(AuditLog.created_at <= end_date)

        # Estatísticas por ação
        stats_query = (
            select(AuditLog.action, func.count().label("count"))
            .where(
                and_(
                    AuditLog.tenant_id == tenant_id,
                    AuditLog.user_id == user_id,
                )
            )
            .group_by(AuditLog.action)
        )

        stats_result = await db.execute(stats_query)
        stats = {row.action: row.count for row in stats_result.all()}

        # Logs
        query = query.order_by(desc(AuditLog.created_at)).limit(limit)
        result = await db.execute(query)
        logs = result.scalars().all()

        return {
            "user_id": str(user_id),
            "total_actions": sum(stats.values()),
            "action_breakdown": stats,
            "logs": [
                {
                    "id": str(log.id),
                    "action": log.action,
                    "entity_type": log.entity_type,
                    "entity_id": log.entity_id,
                    "severity": log.severity,
                    "created_at": (
                        log.created_at.isoformat() if log.created_at else None
                    ),
                }
                for log in logs
            ],
        }

    async def get_security_events(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        severity: Optional[str] = None,
        start_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Recupera eventos de segurança.

        Args:
            db: Sessão do banco de dados
            tenant_id: ID do tenant
            severity: Filtrar por severidade
            start_date: Data inicial
            limit: Limite de resultados

        Returns:
            Lista de eventos de segurança
        """
        query = select(AuditLog).where(
            and_(
                AuditLog.tenant_id == tenant_id,
                AuditLog.entity_type == "SECURITY_EVENT",
            )
        )

        if severity:
            query = query.where(AuditLog.severity == severity)
        if start_date:
            query = query.where(AuditLog.created_at >= start_date)

        query = query.order_by(desc(AuditLog.created_at)).limit(limit)
        result = await db.execute(query)
        logs = result.scalars().all()

        return [
            {
                "id": str(log.id),
                "action": log.action,
                "severity": log.severity,
                "user_id": str(log.user_id) if log.user_id else None,
                "ip_address": log.ip_address,
                "metadata": log.metadata,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ]

    # ========== MANUTENÇÃO ==========

    async def cleanup_old_logs(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        retention_days: int = 365,
    ) -> int:
        """
        Remove logs antigos baseado na política de retenção.

        Args:
            db: Sessão do banco de dados
            tenant_id: ID do tenant
            retention_days: Dias de retenção

        Returns:
            Número de logs removidos
        """
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

        result = await db.execute(
            select(AuditLog).where(
                and_(
                    AuditLog.tenant_id == tenant_id,
                    AuditLog.created_at < cutoff_date,
                    AuditLog.severity == "info",  # Manter warning, error, critical
                )
            )
        )
        old_logs = result.scalars().all()

        count = len(old_logs)
        for log in old_logs:
            await db.delete(log)

        await db.commit()
        logger.info(f"Cleaned up {count} old audit logs for tenant {tenant_id}")
        return count
