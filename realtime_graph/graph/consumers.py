import json
from random import randint
from asyncio import sleep, ensure_future

from channels.generic.websocket import AsyncWebsocketConsumer

class GraphConsumer(AsyncWebsocketConsumer):
    async def run_periodic_task(self, event):
        # print("task started")
        # while True:
        #     await self.send(json.dumps({'value': randint(-20, 20)}))
        #     await sleep(0.5)

        message = event['message']
        await self.send(message)


    async def connect(self):
        self.group_name = 'gui'
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

        # self.my_task = await ensure_future(self.run_periodic_task())


        # for i in range(1000):
        # while True:
        #     await self.send(json.dumps({'value': randint(-20, 20)}))
        #     await sleep(0.5)

    async def disconnect(self, event):
        print('disconnected')
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
