"""Authorization and tenant-isolation tests for WebSocket channels."""

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import WebSocketDisconnect

from app.core.websocket import ConnectionManager
from app.routers import websocket as websocket_module
from app.services.auth_service import AuthService


def _result(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _websocket(headers=None):
    return SimpleNamespace(
        headers=headers or {},
        close=AsyncMock(),
        receive_json=AsyncMock(),
        send_json=AsyncMock(),
        accept=AsyncMock(),
    )


@pytest.mark.asyncio
async def test_websocket_without_jwt_is_rejected():
    websocket = _websocket()
    db = AsyncMock()

    user = await websocket_module._authenticate_websocket(websocket, db)

    assert user is None
    websocket.close.assert_awaited_once_with(
        code=4401, reason="Authentication required"
    )
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_websocket_with_invalid_jwt_is_rejected():
    websocket = _websocket({"sec-websocket-protocol": "bearer, invalid-token"})
    db = AsyncMock()

    user = await websocket_module._authenticate_websocket(websocket, db)

    assert user is None
    websocket.close.assert_awaited_once_with(code=4401, reason="Invalid credentials")
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_valid_jwt_loads_user_from_database_instead_of_trusting_claims():
    user_id = uuid.uuid4()
    database_user = SimpleNamespace(id=user_id, tenant_id=uuid.uuid4())
    token = AuthService.create_access_token(
        {"sub": str(user_id), "tenant_id": str(uuid.uuid4())}
    )
    websocket = _websocket({"sec-websocket-protocol": f"bearer, {token}"})
    db = AsyncMock()
    db.execute.return_value = _result(database_user)

    user = await websocket_module._authenticate_websocket(websocket, db)

    assert user is database_user
    sql = str(db.execute.await_args.args[0])
    assert "users.id" in sql


@pytest.mark.asyncio
async def test_analysis_from_another_tenant_is_not_exposed():
    tenant_id = uuid.uuid4()
    user = SimpleNamespace(id=uuid.uuid4(), tenant_id=tenant_id)
    websocket = _websocket()
    db = AsyncMock()
    db.execute.return_value = _result(None)

    with patch.object(
        websocket_module, "_authenticate_websocket", new=AsyncMock(return_value=user)
    ), patch.object(websocket_module.manager, "connect", new=AsyncMock()) as connect:
        await websocket_module.analysis_progress_ws(websocket, uuid.uuid4(), db=db)

    websocket.close.assert_awaited_once_with(code=4404, reason="Resource not found")
    connect.assert_not_awaited()
    sql = str(db.execute.await_args.args[0])
    assert "analyses.id" in sql
    assert "analyses.tenant_id" in sql


@pytest.mark.asyncio
async def test_own_analysis_uses_tenant_namespaced_channel_and_disconnects():
    tenant_id = uuid.uuid4()
    analysis_id = uuid.uuid4()
    user = SimpleNamespace(id=uuid.uuid4(), tenant_id=tenant_id)
    websocket = _websocket()
    db = AsyncMock()
    db.execute.return_value = _result(SimpleNamespace(id=analysis_id))

    with patch.object(
        websocket_module, "_authenticate_websocket", new=AsyncMock(return_value=user)
    ), patch.object(
        websocket_module.manager,
        "connect",
        new=AsyncMock(return_value="connection-a"),
    ) as connect, patch.object(
        websocket_module,
        "_receive_server_only",
        new=AsyncMock(side_effect=WebSocketDisconnect()),
    ), patch.object(
        websocket_module.manager, "disconnect"
    ) as disconnect:
        await websocket_module.analysis_progress_ws(websocket, analysis_id, db=db)

    assert connect.await_args.args[1] == f"tenant:{tenant_id}:analysis:{analysis_id}"
    disconnect.assert_called_once_with("connection-a")


@pytest.mark.asyncio
async def test_client_tenant_path_cannot_override_authenticated_tenant():
    authenticated_tenant = uuid.uuid4()
    attacker_tenant = uuid.uuid4()
    user = SimpleNamespace(id=uuid.uuid4(), tenant_id=authenticated_tenant)
    websocket = _websocket()

    with patch.object(
        websocket_module, "_authenticate_websocket", new=AsyncMock(return_value=user)
    ), patch.object(
        websocket_module.manager,
        "connect",
        new=AsyncMock(return_value="connection-a"),
    ) as connect, patch.object(
        websocket_module,
        "_receive_server_only",
        new=AsyncMock(side_effect=WebSocketDisconnect()),
    ), patch.object(
        websocket_module.manager, "disconnect"
    ):
        await websocket_module.tenant_ws(
            websocket, tenant_id=str(attacker_tenant), db=AsyncMock()
        )

    assert connect.await_args.args[1] == f"tenant:{authenticated_tenant}"


@pytest.mark.asyncio
async def test_client_message_cannot_broadcast_to_channel():
    websocket = _websocket()
    websocket.receive_json.side_effect = [
        {"type": "analysis_complete", "data": {"forged": True}},
        WebSocketDisconnect(),
    ]

    with patch.object(
        websocket_module.manager, "send_to_connection", new=AsyncMock()
    ) as send, patch.object(
        websocket_module.manager, "broadcast", new=AsyncMock()
    ) as broadcast:
        with pytest.raises(WebSocketDisconnect):
            await websocket_module._receive_server_only(websocket, "connection-a")

    broadcast.assert_not_awaited()
    assert send.await_args.args[1]["payload"]["message"] == (
        "Client publishing is not allowed"
    )


@pytest.mark.asyncio
async def test_server_notifier_broadcasts_only_to_tenant_scoped_channels():
    with patch.object(
        websocket_module.manager, "broadcast", new=AsyncMock()
    ) as broadcast:
        await websocket_module.progress_notifier.notify_progress(
            "analysis-a", "tenant-a", {"percent": 50}
        )

    channels = [call.args[1] for call in broadcast.await_args_list]
    assert channels == [
        "tenant:tenant-a:analysis:analysis-a",
        "tenant:tenant-a",
    ]


def test_disconnect_last_channel_removes_all_connection_state():
    manager = ConnectionManager()
    manager.active_connections = {"tenant:a": {"connection-a": MagicMock()}}
    manager.connection_channels["connection-a"].add("tenant:a")
    manager.connection_metadata["connection-a"] = {"tenant_id": "a"}
    manager.last_ping["connection-a"] = 1.0
    manager.message_history["connection-a"] = [1.0]

    manager.disconnect("connection-a", "tenant:a")

    assert "tenant:a" not in manager.active_connections
    assert "connection-a" not in manager.connection_channels
    assert "connection-a" not in manager.connection_metadata
    assert "connection-a" not in manager.last_ping
    assert "connection-a" not in manager.message_history
