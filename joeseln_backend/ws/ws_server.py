import os
import sys
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError

sys.path.append(os.path.abspath(Path(__file__).parent.parent.parent))

import asyncio
import json

import websockets

from joeseln_backend.auth.security import get_current_jwt_user_for_ws
from joeseln_backend.conf.base_conf import STATIC_WS_TOKEN, WS_INTERNAL_IP, WS_PORT
from joeseln_backend.database.database import SessionLocal
from joeseln_backend.models.models import UserConnectedWs
from joeseln_backend.mylogging.root_logger import logger

connected_clients = set()


async def handle_client(websocket, path):
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
                # print(message)
                await asyncio.wait(
                    [asyncio.create_task(client.send(message)) for client in
                     connected_clients])


    finally:
        # Unregister the client
        try:
            connected_clients.remove(websocket)
            delete_user_connected_ws(ws_id=vars(websocket)['id'])
        except KeyError:
            pass


def add_user_connected_ws(uname, ws_id):
    ws_user = session.query(UserConnectedWs).filter_by(username=uname).first()
    if not ws_user:
        ws_user = UserConnectedWs(username=uname,
                                  ws_id=ws_id,
                                  connected=True)
        try:
            session.add(ws_user)
            session.commit()
        except SQLAlchemyError as e:
            logger.error(e)
    else:
        ws_user.ws_id = ws_id
        ws_user.connected = True
        try:
            session.commit()
        except SQLAlchemyError as e:
            logger.error(e)


def delete_user_connected_ws(ws_id):
    ws_user = session.query(UserConnectedWs).filter_by(ws_id=ws_id).first()
    if ws_user:
        ws_user.connected = False
        try:
            session.commit()
        except SQLAlchemyError as e:
            logger.error(e)


def reset_user_connected_ws():
    init_session = SessionLocal()
    ws_users = init_session.query(UserConnectedWs).all()
    for ws_user in ws_users:
        ws_user.connected = False
    try:
        init_session.commit()
    except SQLAlchemyError as e:
        logger.error(e)


async def main():
    global session
    session = SessionLocal()
    server = await websockets.serve(handle_client, WS_INTERNAL_IP, WS_PORT)
    await server.wait_closed()


if __name__ == "__main__":
    reset_user_connected_ws()
    asyncio.run(main())
