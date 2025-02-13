import sys, os
from pathlib import Path

sys.path.append(os.path.abspath(Path(__file__).parent.parent.parent))

import asyncio
import json
import websockets
from joeseln_backend.auth.security import get_current_keycloak_user_for_ws, \
    get_current_jwt_user_for_ws
from joeseln_backend.conf.base_conf import STATIC_WS_TOKEN, WS_PORT

connected_clients = set()


async def handle_client(websocket, path):
    # Register and authenticate  the new client
    if path.startswith('/ws/jwt_'):
        token = path.split('/ws/jwt_')[1]
        # print('JWT ', token)
        if await get_current_jwt_user_for_ws(token=token):
            connected_clients.add(websocket)

    if path.startswith('/ws/oidc_'):
        token = path.split('/ws/oidc_')[1]
        # print('OIDC ', token)
        if await get_current_keycloak_user_for_ws(token=token):
            connected_clients.add(websocket)

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
        connected_clients.remove(websocket)


async def main():
    server = await websockets.serve(handle_client, "0.0.0.0", WS_PORT)
    await server.wait_closed()


if __name__ == "__main__":
    asyncio.run(main())
