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

from collections import namedtuple
from manager.basic.letter import receving, HeartbeatLetter


Link = namedtuple('Link', "reader writer")


class Linker:

    def __init__(self) -> None:
        self._links = {}  # type: typing.Dict[str, Link]
        self._lis = {}  # type: typing.Dict[str, typing.Any]
        self._queue = asyncio.Queue(256)  # type: asyncio.Queue
        self._manage_queue = asyncio.Queue(256)  # type: asyncio.Queue

    async def new_link(self, linkid: str,
                       host: str = "",
                       port: int = 0) -> None:

        reader, writer = await asyncio.open_connection(host, port)
        self._links[linkid] = Link(reader, writer)

    async def new_listen(self, lisId: str,
                         host: str = "",
                         port: int = 0) -> None:

        server = await asyncio.start_server(self._lis_handle, host, port)
        self._lis[lisId] = server

        asyncio.get_running_loop().\
            create_task(server.serve_forever())

    async def _lis_handle(self, reader: asyncio.StreamReader,
                          writer: asyncio.StreamWriter) -> None:
        # Link init
        first_heart_beat = await receving(reader)

        if not isinstance(first_heart_beat, HeartbeatLetter):
            return

        ident = first_heart_beat.getIdent()
        if ident in self._links:
            return

        self._links[ident] = Link(reader, writer)

        while True:
            letter = await receving(reader)

            if isinstance(letter, HeartbeatLetter):
                await self._manage_queue.put(letter)
            else:
                self._queue.put(letter)

    def exists(self, linkid: str) -> bool:
        return linkid in self._links

    async def run(self) -> None:
        pass


class Connector:

    def __init__(self) -> None:
        pass
