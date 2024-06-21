import json
import websockets
import asyncio


def transmit(db_data):
    async def test(data):
        async with websockets.connect(
                'ws://172.25.74.236:8010/ws/elements/') as websocket:
            try:
                await websocket.send(json.dumps(data))
                response = await websocket.recv()
                # print('transmitted to eln ', response)
            except websockets.exceptions.ConnectionClosedError as e:
                print(e)

    merged_data = {**{'action': 'transmit', 'auth': 'backend_secret'}, **db_data}
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test(merged_data))
