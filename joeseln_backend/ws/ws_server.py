import os
import sys
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError

sys.path.append(os.path.abspath(Path(__file__).parent.parent.parent))

import asyncio
import itertools
import json

import websockets
from websockets.exceptions import ConnectionClosed, ConnectionClosedOK

from joeseln_backend.auth.security import get_current_jwt_user_for_ws
from joeseln_backend.conf.base_conf import STATIC_WS_TOKEN, WS_INTERNAL_IP, WS_PORT
from joeseln_backend.database.database import SessionLocal
from joeseln_backend.models.models import UserConnectedWs
from joeseln_backend.mylogging.root_logger import logger

connected_clients = set()

client_tasks = {}


async def keepalive(websocket, ping_interval=30):
    try:
        for ping in itertools.count():
            await asyncio.sleep(ping_interval)
            await websocket.send(json.dumps({"ping": ping}))
    except (ConnectionClosed, ConnectionClosedOK, asyncio.CancelledError):
        return


async def handle_client(websocket, path):
    # create keepalive task
    keepalive_task = asyncio.create_task(keepalive(websocket))

    # register tasks for cleanup
    client_tasks[websocket] = [keepalive_task]

    # Register and authenticate  the new client
    if path.startswith('/ws/jwt_'):
        token = path.split('/ws/jwt_')[1]
        # print('JWT ', token)
        uname = await get_current_jwt_user_for_ws(token=token)
        if uname:
            connected_clients.add(websocket)
            add_user_connected_ws(uname=uname, ws_id=vars(websocket)['id'])

    if path.startswith(f'/ws/{STATIC_WS_TOKEN}'):
        # print('BACKEND_CLIENT')
        connected_clients.add(websocket)

    try:
        async for message in websocket:
            # Broadcast the message from backend to all connected clients
            message_as_dict = json.loads(message)
            # print('connected clients ', len(connected_clients))
            if message_as_dict['auth'] == STATIC_WS_TOKEN:
                del message_as_dict['auth']
                message = json.dumps(message_as_dict)

                # broadcast safely
                results = await asyncio.gather(
                    *(client.send(message) for client in connected_clients),
                    return_exceptions=True
                )

                for client, result in zip(list(connected_clients), results):
                    if isinstance(result, Exception):
                        logger.warning(
                            f"WS send failed for client {client.id}: {type(result).__name__}"
                        )

                        # remove dead/broken clients
                        if isinstance(result,
                                      (ConnectionClosed, ConnectionClosedOK)):
                            connected_clients.discard(client)

    except (ConnectionClosed, ConnectionClosedOK):
        pass

    finally:
        # Unregister the client
        connected_clients.discard(websocket)
        delete_user_connected_ws(ws_id=vars(websocket)['id'])

        # cancel tasks
        for task in client_tasks.pop(websocket, []):
            task.cancel()
            try:
                await task
            except Exception:
                pass

        # close websocket cleanly
        try:
            await websocket.close()
            await websocket.wait_closed()
        except Exception:
            pass


def add_user_connected_ws(uname, ws_id):
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


async def main():
    server = await websockets.serve(
        handle_client, WS_INTERNAL_IP, WS_PORT, max_size=1024
    )
    await server.wait_closed()


if __name__ == "__main__":
    reset_user_connected_ws()
    asyncio.run(main())
