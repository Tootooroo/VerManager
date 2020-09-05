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

import asyncio
import typing

from manager.basic.util import loop_forever_async
from manager.basic.letter import receving, sending, HeartbeatLetter


class Link:

    PASSIVE = 0
    ACTIVE = 1

    def __init__(self, reader: asyncio.StreamReader,
                 writer: asyncio.StreamWriter,
                 isActive: int) -> None:
        self.reader = reader
        self.writer = writer
        self.hbCount = 0
        self.isActive = isActive


class Linker:

    def __init__(self) -> None:
        self._links = {}  # type: typing.Dict[str, Link]
        self._lis = {}  # type: typing.Dict[str, typing.Any]
        self._queue = asyncio.Queue(256)  # type: asyncio.Queue
        self._manage_queue = asyncio.Queue(256)  # type: asyncio.Queue
        self._loop = asyncio.get_running_loop()
        self._hostname = ""

    def set_host_name(self, name: str) -> None:
        self._hostname = name

    async def new_link(self, linkid: str,
                       host: str = "",
                       port: int = 0) -> None:

        reader, writer = await asyncio.open_connection(host, port)

        await sending(writer, HeartbeatLetter(self._hostname, 0))
        self._links[linkid] = Link(reader, writer, Link.ACTIVE)

        self._loop.create_task(self._active_link(reader, writer, linkid))

    async def _active_link(self, reader: asyncio.StreamReader,
                           writer: asyncio.StreamWriter,
                           linkid: str) -> None:
        # Link Init
        first_heart_beat = HeartbeatLetter(self._hostname, 0)
        await sending(writer, first_heart_beat)

        try:
            heartbeat = await receving(reader, timeout=3)
        except asyncio.exceptions.TimeoutError:
            del self._links[linkid]

        if not isinstance(heartbeat, HeartbeatLetter):
            del self._links[linkid]

        await self._manage_queue.put(heartbeat)

        while True:
            letter = await receving(reader)
            if isinstance(letter, HeartbeatLetter):
                await self._manage_queue.put(letter)
            else:
                await self._queue.put(letter)

    async def new_listen(self, lisId: str,
                         host: str = "",
                         port: int = 0) -> None:

        server = await asyncio.start_server(self._passive_link, host, port)
        self._lis[lisId] = server

        asyncio.get_running_loop().\
            create_task(server.serve_forever())

    async def _passive_link(self, reader: asyncio.StreamReader,
                            writer: asyncio.StreamWriter) -> None:
        # Link init
        try:
            first_heart_beat = await receving(reader, timeout=3)
        except asyncio.exceptions.TimeoutError:
            return

        if isinstance(first_heart_beat, HeartbeatLetter):
            ident = first_heart_beat.getIdent()
            if ident in self._links:
                return

            self._links[ident] = Link(reader, writer, Link.PASSIVE)
        else:
            return

        # Send the first heartbaeat to manage queue
        await self._manage_queue.put(first_heart_beat)

        while True:
            letter = await receving(reader)
            if isinstance(letter, HeartbeatLetter):
                await self._manage_queue.put(letter)
            else:
                self._queue.put(letter)

    def exists(self, linkid: str) -> bool:
        return linkid in self._links

    async def run(self) -> None:
        while True:
            heartbeat = await self._manage_queue.get()
            if not isinstance(heartbeat, HeartbeatLetter):
                return

            ident = heartbeat.getIdent()
            if ident not in self._links:
                return

            link = self._links[ident]
            seq = heartbeat.getSeq()

            if link.hbCount != seq:
                return
            else:
                link.hbCount += 1

            if link.isActive:
                self._loop.create_task(self._next_heartbeat(link, 2))
            else:
                await sending(link.writer, heartbeat)

    def start(self) -> None:
        self._loop.create_task(self.run())

    async def _next_heartbeat(self, link: Link, delay: int) -> None:
        await asyncio.sleep(delay)

        hb = HeartbeatLetter(self._hostname, link.hbCount)
        await sending(link.writer, hb)


class Connector:

    def __init__(self) -> None:
        pass
