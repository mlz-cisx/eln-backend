import json
import websockets
import asyncio

from joeseln_backend.mylogging.root_logger import logger
from joeseln_backend.conf.base_conf import WS_URL, STATIC_WS_TOKEN


def transmit(db_data):
    async def test(data):
        async with websockets.connect(
                f'{WS_URL}{STATIC_WS_TOKEN}') as websocket:
            try:
                await websocket.send(json.dumps(data))
                response = await websocket.recv()
                # print('transmitted to eln ', response)
            except websockets.exceptions.ConnectionClosedError as e:
                logger.error(e)

    merged_data = {**{'action': 'transmit', 'auth': STATIC_WS_TOKEN},
                   **db_data}
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test(merged_data))
