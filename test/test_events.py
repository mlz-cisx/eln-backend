import asyncio
import json
import uuid
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from joeseln_backend.auth import security
from joeseln_backend.ws import events


def test_event_hub_broadcasts_json_to_each_registered_client():
    hub = events.EventHub()
    first = hub.register()
    second = hub.register()

    assert hub.client_count == 2
    hub.publish({"event": "changed", "id": uuid.UUID(int=1)})

    expected = {"event": "changed", "id": str(uuid.UUID(int=1))}
    assert json.loads(first.get_nowait()) == expected
    assert json.loads(second.get_nowait()) == expected

    hub.unregister(first)
    hub.unregister(first)
    assert hub.client_count == 1
    hub.publish({"event": "deleted"})
    assert json.loads(second.get_nowait()) == {"event": "deleted"}
    assert first.empty()


def test_event_hub_drops_only_events_for_full_clients(monkeypatch):
    hub = events.EventHub(max_queue_size=1)
    full = hub.register()
    available = hub.register()
    full.put_nowait("previous event")
    warning = MagicMock()
    monkeypatch.setattr(events.logger, "warning", warning)

    hub.publish({"event": "new"})

    assert full.get_nowait() == "previous event"
    assert json.loads(available.get_nowait()) == {"event": "new"}
    warning.assert_called_once_with("SSE client queue full; dropping event")


def test_transmit_uses_shared_hub(monkeypatch):
    publish = MagicMock()
    monkeypatch.setattr(events.hub, "publish", publish)
    payload = {"event": "created"}

    events.transmit(payload)

    publish.assert_called_once_with(payload)


def test_add_user_connected_ws_creates_connection(monkeypatch):
    db = MagicMock()
    db.query.return_value.filter_by.return_value.first.return_value = None
    monkeypatch.setattr(events, "SessionLocal", lambda: db)
    ws_id = uuid.uuid4()

    events.add_user_connected_ws("alice", ws_id)

    db.query.return_value.filter_by.assert_called_once_with(username="alice")
    (connection,) = db.add.call_args.args
    assert connection.username == "alice"
    assert connection.ws_id == ws_id
    assert connection.connected is True
    db.commit.assert_called_once()
    db.close.assert_called_once()


def test_add_user_connected_ws_updates_existing_connection(monkeypatch):
    db = MagicMock()
    connection = MagicMock()
    db.query.return_value.filter_by.return_value.first.return_value = connection
    monkeypatch.setattr(events, "SessionLocal", lambda: db)
    ws_id = uuid.uuid4()

    events.add_user_connected_ws("alice", ws_id)

    assert connection.ws_id == ws_id
    assert connection.connected is True
    db.add.assert_not_called()
    db.commit.assert_called_once()
    db.close.assert_called_once()


@pytest.mark.parametrize("connection", [None, MagicMock()])
def test_delete_user_connected_ws_updates_only_existing_connection(
    monkeypatch, connection
):
    db = MagicMock()
    db.query.return_value.filter_by.return_value.first.return_value = connection
    monkeypatch.setattr(events, "SessionLocal", lambda: db)
    ws_id = uuid.uuid4()

    events.delete_user_connected_ws(ws_id)

    db.query.return_value.filter_by.assert_called_once_with(ws_id=ws_id)
    if connection is None:
        db.commit.assert_not_called()
    else:
        assert connection.connected is False
        db.commit.assert_called_once()
    db.close.assert_called_once()


def test_reset_user_connected_ws_disconnects_every_connection(monkeypatch):
    db = MagicMock()
    connections = [MagicMock(), MagicMock()]
    db.query.return_value.all.return_value = connections
    monkeypatch.setattr(events, "SessionLocal", lambda: db)

    events.reset_user_connected_ws()

    assert all(connection.connected is False for connection in connections)
    db.commit.assert_called_once()
    db.close.assert_called_once()


@pytest.mark.parametrize(
    "operation,args",
    [
        ("add_user_connected_ws", ("alice", uuid.UUID(int=1))),
        ("delete_user_connected_ws", (uuid.UUID(int=1),)),
        ("reset_user_connected_ws", ()),
    ],
)
def test_connection_operations_roll_back_and_close_on_database_error(
    monkeypatch, operation, args
):
    db = MagicMock()
    db.query.side_effect = SQLAlchemyError("database unavailable")
    monkeypatch.setattr(events, "SessionLocal", lambda: db)
    error = MagicMock()
    monkeypatch.setattr(events.logger, "error", error)

    getattr(events, operation)(*args)

    db.rollback.assert_called_once()
    db.commit.assert_not_called()
    db.close.assert_called_once()
    error.assert_called_once()


@pytest.mark.asyncio
async def test_sse_events_rejects_unauthenticated_client(monkeypatch):
    async def reject(_token):
        return None

    monkeypatch.setattr(security, "get_current_jwt_user_for_ws", reject)
    register = MagicMock()
    monkeypatch.setattr(events.hub, "register", register)

    with pytest.raises(HTTPException) as exc:
        await events.sse_events(token="invalid")

    assert exc.value.status_code == 401
    register.assert_not_called()


@pytest.mark.asyncio
async def test_sse_events_streams_events_and_cleans_up(monkeypatch):
    async def authenticate(token):
        assert token == "valid"
        return "alice"

    monkeypatch.setattr(security, "get_current_jwt_user_for_ws", authenticate)
    queue = asyncio.Queue()
    monkeypatch.setattr(events.hub, "register", lambda: queue)
    unregister = MagicMock()
    add_connection = MagicMock()
    delete_connection = MagicMock()
    monkeypatch.setattr(events.hub, "unregister", unregister)
    monkeypatch.setattr(events, "add_user_connected_ws", add_connection)
    monkeypatch.setattr(events, "delete_user_connected_ws", delete_connection)

    response = await events.sse_events(token="valid")
    stream = response.body_iterator
    assert response.media_type == "text/event-stream"
    assert response.headers["cache-control"] == "no-cache"
    assert response.headers["x-accel-buffering"] == "no"
    assert await anext(stream) == ": connected\n\n"

    queue.put_nowait('{"event": "changed"}')
    assert await anext(stream) == 'data: {"event": "changed"}\n\n'
    add_connection.assert_called_once()
    assert add_connection.call_args.kwargs["uname"] == "alice"
    ws_id = add_connection.call_args.kwargs["ws_id"]

    await stream.aclose()

    unregister.assert_called_once_with(queue)
    delete_connection.assert_called_once_with(ws_id=ws_id)


@pytest.mark.asyncio
async def test_sse_events_sends_keepalive_after_timeout(monkeypatch):
    async def authenticate(_token):
        return "alice"

    async def timeout(_awaitable, timeout):
        assert timeout == events.SSE_PING_INTERVAL_SECONDS
        _awaitable.close()
        raise asyncio.TimeoutError

    monkeypatch.setattr(security, "get_current_jwt_user_for_ws", authenticate)
    monkeypatch.setattr(events.asyncio, "wait_for", timeout)
    monkeypatch.setattr(events, "add_user_connected_ws", MagicMock())
    monkeypatch.setattr(events, "delete_user_connected_ws", MagicMock())

    response = await events.sse_events(token="valid")
    stream = response.body_iterator
    assert await anext(stream) == ": connected\n\n"
    assert await anext(stream) == ": keepalive\n\n"
    await stream.aclose()

    assert events.hub.client_count == 0
    events.delete_user_connected_ws.assert_called_once()
