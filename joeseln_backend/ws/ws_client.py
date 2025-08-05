import asyncio
import json

import websockets

from joeseln_backend.conf.base_conf import STATIC_WS_TOKEN, WS_URL
from joeseln_backend.mylogging.root_logger import logger


class WebSocketClient:
    def __init__(self, url, token):
        self.url = url
        self.token = token
        self.websocket = None

    async def connect(self):
        try:
            self.websocket = await websockets.connect(f'{self.url}{self.token}')
        except Exception as e:
            logger.error(f"Failed to connect: {e}")

    async def transmit(self, db_data):
        if self.websocket is None or self.websocket.closed:
            await self.connect()

        if self.websocket is not None:
            try:
                merged_data = {**{'action': 'transmit', 'auth': self.token}, **db_data}
                await self.websocket.send(json.dumps(merged_data))
                _ = await self.websocket.recv()
                # response = await self.websocket.recv()
                # print('transmitted to eln ', response)
            except websockets.exceptions.ConnectionClosedError as e:
                logger.error(e)
                await self.connect()
            except Exception as e:
                logger.error(e)

    async def close(self):
        if self.websocket is not None:
            await self.websocket.close()


ws_client = WebSocketClient(WS_URL, STATIC_WS_TOKEN)

def transmit(db_data):
    asyncio.run(ws_client.transmit(db_data))
