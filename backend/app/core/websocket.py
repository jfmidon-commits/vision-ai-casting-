"""
WebSocket Manager - Sistema de comunicacao em tempo real do Vision Ecosystem.

Responsabilidades:
- Gerenciar conexoes WebSocket por canal/room
- Broadcast de mensagens para multiplos clientes
- Rooms privadas (por tenant, usuario, projeto)
- Eventos em tempo real (analises, notificacoes, progresso)
- Reconexao automatica e heartbeat
- Rate limiting por conexao
"""

import asyncio
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel


class WebSocketMessage(BaseModel):
    """Modelo padronizado de mensagem WebSocket."""

    event_type: str
    payload: Dict[str, Any]
    channel: Optional[str] = None
    timestamp: Optional[float] = None
    sender_id: Optional[str] = None

    def __init__(self, **data):
        super().__init__(**data)
        if self.timestamp is None:
            self.timestamp = time.time()


class ConnectionManager:
    """
    Gerenciador de conexoes WebSocket com suporte a rooms,
    broadcast, mensagens privadas e heartbeat.
    """

    def __init__(self):
        # Conexoes ativas: channel -> {connection_id: WebSocket}
        self.active_connections: Dict[str, Dict[str, WebSocket]] = {}

        # Mapeamento reverso: connection_id -> [channels]
        self.connection_channels: Dict[str, Set[str]] = defaultdict(set)

        # Metadados da conexao: connection_id -> metadata
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}

        # Rate limiting: connection_id -> [timestamps]
        self.message_history: Dict[str, List[float]] = defaultdict(list)
        self.rate_limit = 30  # mensagens por minuto
        self.rate_window = 60  # segundos

        # Heartbeat tracking
        self.last_ping: Dict[str, float] = {}
        self.heartbeat_interval = 30  # segundos
        self.heartbeat_timeout = 60  # segundos

        # Contadores
        self.total_connections = 0
        self.total_messages = 0
        self.total_disconnects = 0

    # ========== CONEXAO ==========

    async def connect(
        self,
        websocket: WebSocket,
        channel: str,
        connection_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Aceita uma nova conexao WebSocket em um canal.

        Args:
            websocket: Objeto WebSocket do FastAPI
            channel: Nome do canal/room
            connection_id: ID unico da conexao (gerado se nao fornecido)
            metadata: Metadados opcionais (user_id, tenant_id, etc.)

        Returns:
            connection_id: ID da conexao estabelecida
        """
        await websocket.accept()

        if connection_id is None:
            connection_id = f"conn_{int(time.time() * 1000)}_{id(websocket)}"

        # Registrar no canal
        if channel not in self.active_connections:
            self.active_connections[channel] = {}
        self.active_connections[channel][connection_id] = websocket

        # Registrar mapeamento reverso
        self.connection_channels[connection_id].add(channel)

        # Registrar metadados
        self.connection_metadata[connection_id] = metadata or {}
        self.connection_metadata[connection_id].update(
            {
                "connected_at": time.time(),
                "channel": channel,
                "connection_id": connection_id,
            }
        )

        # Heartbeat
        self.last_ping[connection_id] = time.time()

        self.total_connections += 1

        # Enviar confirmacao de conexao
        await self.send_to_connection(
            connection_id,
            {
                "event_type": "connected",
                "payload": {
                    "connection_id": connection_id,
                    "channel": channel,
                    "timestamp": time.time(),
                },
            },
        )

        return connection_id

    def disconnect(self, connection_id: str, channel: Optional[str] = None):
        """
        Desconecta uma conexao.

        Args:
            connection_id: ID da conexao
            channel: Canal especifico (se None, desconecta de todos)
        """
        if channel:
            # Desconectar de um canal especifico
            if channel in self.active_connections:
                self.active_connections[channel].pop(connection_id, None)
                if not self.active_connections[channel]:
                    del self.active_connections[channel]
            channels = self.connection_channels.get(connection_id)
            if channels is not None:
                channels.discard(channel)
                if not channels:
                    self.connection_channels.pop(connection_id, None)
                    self.connection_metadata.pop(connection_id, None)
                    self.last_ping.pop(connection_id, None)
                    self.message_history.pop(connection_id, None)
        else:
            # Desconectar de todos os canais
            channels = list(self.connection_channels.get(connection_id, []))
            for ch in channels:
                if ch in self.active_connections:
                    self.active_connections[ch].pop(connection_id, None)
                    if not self.active_connections[ch]:
                        del self.active_connections[ch]

            self.connection_channels.pop(connection_id, None)
            self.connection_metadata.pop(connection_id, None)
            self.last_ping.pop(connection_id, None)
            self.message_history.pop(connection_id, None)

        self.total_disconnects += 1

    # ========== ENVIO DE MENSAGENS ==========

    async def send_to_connection(
        self, connection_id: str, message: Dict[str, Any]
    ) -> bool:
        """
        Envia mensagem para uma conexao especifica.

        Args:
            connection_id: ID da conexao
            message: Mensagem a ser enviada

        Returns:
            True se enviado com sucesso, False caso contrario
        """
        # Encontrar o WebSocket
        websocket = None
        for channel, connections in self.active_connections.items():
            if connection_id in connections:
                websocket = connections[connection_id]
                break

        if websocket is None:
            return False

        try:
            if isinstance(message, WebSocketMessage):
                msg_dict = message.dict()
            else:
                msg_dict = message

            await websocket.send_json(msg_dict)
            self.total_messages += 1
            return True
        except Exception:
            # Conexao provavelmente fechada
            self.disconnect(connection_id)
            return False

    async def broadcast(
        self, message: Dict[str, Any], channel: str, exclude: Optional[List[str]] = None
    ) -> int:
        """
        Envia mensagem para todos as conexoes em um canal.

        Args:
            message: Mensagem a ser broadcastada
            channel: Nome do canal
            exclude: Lista de connection_ids para excluir

        Returns:
            Numero de clientes que receberam a mensagem
        """
        if channel not in self.active_connections:
            return 0

        exclude_set = set(exclude or [])
        connections = dict(
            self.active_connections[channel]
        )  # Copia para evitar modificacao durante iteracao

        sent_count = 0
        disconnected = []

        for connection_id, websocket in connections.items():
            if connection_id in exclude_set:
                continue

            try:
                if isinstance(message, WebSocketMessage):
                    msg_dict = message.dict()
                else:
                    msg_dict = message

                await websocket.send_json(msg_dict)
                sent_count += 1
                self.total_messages += 1
            except Exception:
                disconnected.append(connection_id)

        # Limpar conexoes quebradas
        for conn_id in disconnected:
            self.disconnect(conn_id, channel)

        return sent_count

    async def broadcast_to_user(self, message: Dict[str, Any], user_id: str) -> int:
        """
        Envia mensagem para todas as conexoes de um usuario.

        Args:
            message: Mensagem a ser enviada
            user_id: ID do usuario

        Returns:
            Numero de conexoes que receberam
        """
        sent_count = 0
        disconnected = []

        for channel, connections in self.active_connections.items():
            for connection_id, websocket in connections.items():
                metadata = self.connection_metadata.get(connection_id, {})
                if metadata.get("user_id") == user_id:
                    try:
                        await websocket.send_json(message)
                        sent_count += 1
                        self.total_messages += 1
                    except Exception:
                        disconnected.append(connection_id)

        for conn_id in disconnected:
            self.disconnect(conn_id)

        return sent_count

    async def broadcast_to_tenant(self, message: Dict[str, Any], tenant_id: str) -> int:
        """
        Envia mensagem para todas as conexoes de um tenant.

        Args:
            message: Mensagem a ser enviada
            tenant_id: ID do tenant

        Returns:
            Numero de conexoes que receberam
        """
        sent_count = 0
        disconnected = []

        for channel, connections in self.active_connections.items():
            for connection_id, websocket in connections.items():
                metadata = self.connection_metadata.get(connection_id, {})
                if metadata.get("tenant_id") == tenant_id:
                    try:
                        await websocket.send_json(message)
                        sent_count += 1
                        self.total_messages += 1
                    except Exception:
                        disconnected.append(connection_id)

        for conn_id in disconnected:
            self.disconnect(conn_id)

        return sent_count

    # ========== EVENTOS ESPECIFICOS ==========

    async def emit_analysis_progress(
        self,
        channel: str,
        analysis_id: str,
        progress: float,
        status: str,
        details: Optional[Dict] = None,
    ) -> int:
        """Emite evento de progresso de analise."""
        return await self.broadcast(
            {
                "event_type": "analysis_progress",
                "payload": {
                    "analysis_id": analysis_id,
                    "progress": round(progress, 2),
                    "status": status,
                    "details": details or {},
                    "timestamp": time.time(),
                },
            },
            channel,
        )

    async def emit_analysis_complete(
        self,
        channel: str,
        analysis_id: str,
        result: Dict[str, Any],
    ) -> int:
        """Emite evento de analise completa."""
        return await self.broadcast(
            {
                "event_type": "analysis_complete",
                "payload": {
                    "analysis_id": analysis_id,
                    "result": result,
                    "timestamp": time.time(),
                },
            },
            channel,
        )

    async def emit_notification(
        self,
        channel: str,
        notification_type: str,
        title: str,
        message: str,
        data: Optional[Dict] = None,
    ) -> int:
        """Emite notificacao para um canal."""
        return await self.broadcast(
            {
                "event_type": "notification",
                "payload": {
                    "type": notification_type,
                    "title": title,
                    "message": message,
                    "data": data or {},
                    "timestamp": time.time(),
                },
            },
            channel,
        )

    async def emit_casting_update(
        self,
        channel: str,
        casting_id: str,
        update_type: str,
        data: Dict[str, Any],
    ) -> int:
        """Emite atualizacao de casting."""
        return await self.broadcast(
            {
                "event_type": "casting_update",
                "payload": {
                    "casting_id": casting_id,
                    "update_type": update_type,
                    "data": data,
                    "timestamp": time.time(),
                },
            },
            channel,
        )

    async def emit_agent_execution(
        self,
        channel: str,
        agent_name: str,
        intent: str,
        result: Dict[str, Any],
    ) -> int:
        """Emite resultado de execucao de agente."""
        return await self.broadcast(
            {
                "event_type": "agent_execution",
                "payload": {
                    "agent_name": agent_name,
                    "intent": intent,
                    "result": result,
                    "timestamp": time.time(),
                },
            },
            channel,
        )

    # ========== RATE LIMITING ==========

    def check_rate_limit(self, connection_id: str) -> bool:
        """
        Verifica se a conexao respeita o rate limit.

        Args:
            connection_id: ID da conexao

        Returns:
            True se dentro do limite, False se excedido
        """
        now = time.time()
        history = self.message_history[connection_id]

        # Remover mensagens antigas fora da janela
        history[:] = [t for t in history if now - t < self.rate_window]

        if len(history) >= self.rate_limit:
            return False

        history.append(now)
        return True

    # ========== HEARTBEAT ==========

    async def handle_ping(self, connection_id: str):
        """Processa ping de uma conexao."""
        self.last_ping[connection_id] = time.time()

        # Enviar pong
        await self.send_to_connection(
            connection_id,
            {
                "event_type": "pong",
                "payload": {"timestamp": time.time()},
            },
        )

    async def cleanup_stale_connections(self):
        """Remove conexoes que nao responderam ao heartbeat."""
        now = time.time()
        stale = []

        for connection_id, last_ping_time in self.last_ping.items():
            if now - last_ping_time > self.heartbeat_timeout:
                stale.append(connection_id)

        for conn_id in stale:
            self.disconnect(conn_id)

        return len(stale)

    async def start_heartbeat_monitor(self):
        """Inicia loop de monitoramento de heartbeat."""
        while True:
            await asyncio.sleep(self.heartbeat_interval)
            cleaned = await self.cleanup_stale_connections()
            if cleaned > 0:
                print(f"[WebSocket] {cleaned} conexoes stale removidas")

    # ========== ESTATISTICAS ==========

    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatisticas do WebSocket manager."""
        total_active = sum(len(conns) for conns in self.active_connections.values())

        return {
            "total_active_connections": total_active,
            "total_channels": len(self.active_connections),
            "total_connections_lifetime": self.total_connections,
            "total_disconnects": self.total_disconnects,
            "total_messages_sent": self.total_messages,
            "channels": {
                channel: len(conns)
                for channel, conns in self.active_connections.items()
            },
        }

    def get_channel_stats(self, channel: str) -> Dict[str, Any]:
        """Retorna estatisticas de um canal especifico."""
        if channel not in self.active_connections:
            return {"exists": False, "connections": 0}

        connections = self.active_connections[channel]
        return {
            "exists": True,
            "connections": len(connections),
            "connection_ids": list(connections.keys()),
        }


# Instancia global do manager
manager = ConnectionManager()


# ========== FASTAPI ENDPOINT HELPERS ==========


async def websocket_endpoint_handler(
    websocket: WebSocket,
    channel: str,
    user_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
):
    """
    Handler padrao para endpoints WebSocket no FastAPI.

    Uso:
        @router.websocket("/ws/{channel}")
        async def websocket_endpoint(websocket: WebSocket, channel: str):
            await websocket_endpoint_handler(websocket, channel, user_id="...")
    """
    connection_id = await manager.connect(
        websocket=websocket,
        channel=channel,
        metadata={
            "user_id": user_id,
            "tenant_id": tenant_id,
        },
    )

    try:
        while True:
            # Receber mensagem
            data = await websocket.receive_json()

            # Rate limiting
            if not manager.check_rate_limit(connection_id):
                await manager.send_to_connection(
                    connection_id,
                    {
                        "event_type": "error",
                        "payload": {"message": "Rate limit exceeded. Slow down."},
                    },
                )
                continue

            # Processar mensagem
            event_type = data.get("event_type", "unknown")

            if event_type == "ping":
                await manager.handle_ping(connection_id)
            elif event_type == "subscribe":
                new_channel = data.get("payload", {}).get("channel")
                if new_channel:
                    await manager.connect(
                        websocket=websocket,
                        channel=new_channel,
                        connection_id=connection_id,
                        metadata=manager.connection_metadata.get(connection_id, {}),
                    )
            elif event_type == "unsubscribe":
                old_channel = data.get("payload", {}).get("channel")
                if old_channel:
                    manager.disconnect(connection_id, old_channel)
            else:
                # Echo para o canal (ou processar conforme necessario)
                await manager.broadcast(
                    {
                        "event_type": "echo",
                        "payload": {
                            "original_event": event_type,
                            "data": data.get("payload", {}),
                        },
                    },
                    channel,
                    exclude=[connection_id],
                )

    except WebSocketDisconnect:
        manager.disconnect(connection_id)
    except Exception:
        manager.disconnect(connection_id)
        raise
