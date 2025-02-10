import asyncio
import json
import websockets
from joeseln_backend.auth.security import get_current_keycloak_user_for_ws, \
    get_current_jwt_user_for_ws
from joeseln_backend.conf.base_conf import STATIC_WS_TOKEN, \
    KEYCLOAK_INTEGRATION, WS_PORT

connected_clients = set()


async def handle_client(websocket, path):
    # Register the new client
    connected_clients.add(websocket)
    try:

        async for message in websocket:
            # Broadcast the message to all connected clients
            message_as_dict = json.loads(message)
            print('conncted clients ', len(connected_clients))
            await asyncio.wait(
                [client.send(message) for client in connected_clients])
            if message_as_dict['auth'] == STATIC_WS_TOKEN:
                # we don't want to transmit any token
                del message_as_dict['auth']
                message = json.dumps(message_as_dict)
                print(message)
                await asyncio.wait(
                    [client.send(message) for client in connected_clients])

            elif KEYCLOAK_INTEGRATION and message_as_dict[
                'auth'] and '__zone_symbol__value' in json.loads(
                json.dumps(message_as_dict['auth'])):
                # we don't want to transmit any token
                token = json.loads(json.dumps(message_as_dict['auth']))[
                    '__zone_symbol__value']
                if await get_current_keycloak_user_for_ws(token=token):
                    del message_as_dict['auth']
                    message = json.dumps(message_as_dict)
                    print(message)
                    await asyncio.wait(
                        [client.send(message) for client in connected_clients])

            else:
                # we don't want to transmit any token
                token = message_as_dict['auth']
                if await get_current_jwt_user_for_ws(token=token):
                    del message_as_dict['auth']
                    message = json.dumps(message_as_dict)
                    print(message)
                    await asyncio.wait(
                        [client.send(message) for client in connected_clients])

    finally:
        # Unregister the client
        connected_clients.remove(websocket)


async def main():
    server = await websockets.serve(handle_client, "0.0.0.0", WS_PORT)
    await server.wait_closed()


if __name__ == "__main__":
    asyncio.run(main())
