# MIT License
#
# Copyright (c) 2020 Gcom
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from channels.generic.websocket import AsyncWebsocketConsumer
from client.models import Clients
from typing import Dict, Any
from channels.db import database_sync_to_async


class CommuConsumer(AsyncWebsocketConsumer):

    async def connect(self) -> None:
        await client_create(self.channel_name)

    async def disconnect(self, close_code) -> None:
        await client_delete(self.channel_name)

    async def server_message(self, event: Dict[str, Any]) -> None:
        # Message from server to client.
        await self.send(event['letter'].toString())


async def client_create(name: str) -> None:
    await database_sync_to_async(
        Clients.objects.create
    )(client_name=name)


async def client_delete(name: str) -> None:
    client = await database_sync_to_async(
        Clients.objects.filter
    )(client_name=name)

    await database_sync_to_async(
        client.delete
    )()
