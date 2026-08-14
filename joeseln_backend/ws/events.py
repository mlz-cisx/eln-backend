"""Server-Sent Events (SSE) notification hub.

replaces the standalone WebSocket broadcast server (``ws_server.py``) and the
internal WS client (``ws_client.py``)

"""

import asyncio
import json
import uuid

from fastapi import APIRouter, Header, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.exc import SQLAlchemyError

from joeseln_backend.database.database import SessionLocal
from joeseln_backend.mylogging.root_logger import logger

SSE_PING_INTERVAL_SECONDS = 30
SSE_QUEUE_MAXSIZE = 100


class EventHub:
    """Collect JSON notification events to connected SSE streams.

    ``publish`` is synchronous and non-blocking, so it is safe to call from
    request handlers and from SQLAlchemy event listeners.
    """

    def __init__(self, max_queue_size=SSE_QUEUE_MAXSIZE):
        self._queues = set()
        self._max_queue_size = max_queue_size

    def register(self) -> asyncio.Queue:
        queue = asyncio.Queue(maxsize=self._max_queue_size)
        self._queues.add(queue)
        return queue

    def unregister(self, queue) -> None:
        self._queues.discard(queue)

    def publish(self, data) -> None:
        message = json.dumps(data, default=str)
        for queue in list(self._queues):
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                logger.warning("SSE client queue full; dropping event")

    @property
    def client_count(self) -> int:
        return len(self._queues)


hub = EventHub()


def transmit(data):
    """Publish a notification event to all connected SSE clients.

    Synchronous, non-blocking, and safe with or without a running event loop
    """
    hub.publish(data)


def add_user_connected_ws(uname, ws_id):
    # prevent circular import
    from joeseln_backend.models.models import UserConnectedWs

    db = SessionLocal()
    try:
        ws_user = db.query(UserConnectedWs).filter_by(username=uname).first()
        if not ws_user:
            ws_user = UserConnectedWs(username=uname, ws_id=ws_id, connected=True)
            db.add(ws_user)
        else:
            ws_user.ws_id = ws_id
            ws_user.connected = True
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(e)
    finally:
        db.close()


def delete_user_connected_ws(ws_id):
    from joeseln_backend.models.models import UserConnectedWs

    db = SessionLocal()
    try:
        ws_user = db.query(UserConnectedWs).filter_by(ws_id=ws_id).first()
        if ws_user:
            ws_user.connected = False
            db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(e)
    finally:
        db.close()


def reset_user_connected_ws():
    from joeseln_backend.models.models import UserConnectedWs

    db = SessionLocal()
    try:
        ws_users = db.query(UserConnectedWs).all()
        for ws_user in ws_users:
            ws_user.connected = False
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(e)
    finally:
        db.close()


events_router = APIRouter(prefix="/api")


@events_router.get("/events")
async def sse_events(
    token: str = Query(default=""), authorization: str = Header(default="")
):
    """stream notification events to the authenticated browser."""
    # prevent circular import
    from joeseln_backend.auth.security import get_current_jwt_user_for_ws

    if not token and authorization.startswith("Bearer "):
        token = authorization[len("Bearer ") :].strip()

    uname = await get_current_jwt_user_for_ws(token)
    if not uname:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    ws_id = uuid.uuid4()
    queue = hub.register()
    add_user_connected_ws(uname=uname, ws_id=ws_id)

    async def event_stream():
        try:
            yield ": connected\n\n"
            while True:
                try:
                    message = await asyncio.wait_for(
                        queue.get(), timeout=SSE_PING_INTERVAL_SECONDS
                    )
                    yield f"data: {message}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            hub.unregister(queue)
            delete_user_connected_ws(ws_id=ws_id)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            # disable response buffering in nginx
            "X-Accel-Buffering": "no",
        },
    )
