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
from manager.basic.util import delayExec
from manager.basic.letter import receving, sending, HeartbeatLetter, Letter


class Link:

    # Role
    PASSIVE = 0
    ACTIVE = 1

    # state
    CONNECTED = 0
    RECONNECTING = 1
    DISCONNECTED = 2
    REMOVED = 3

    def __init__(self, ident: str, host: str, port: int,
                 reader: asyncio.StreamReader,
                 writer: asyncio.StreamWriter,
                 isActive: int) -> None:
        self.ident = ident
        self.reader = reader
        self.writer = writer
        self.hbCount = 0
        self.isActive = isActive
        self.state = Link.CONNECTED

        self.host = host
        self.port = port


class Linker:

    def __init__(self) -> None:
        self._links = {}  # type: typing.Dict[str, Link]
        self._lis = {}  # type: typing.Dict[str, typing.Any]
        self._manage_queue = asyncio.Queue(256)  # type: asyncio.Queue
        self.msg_callback = None  # type: typing.Optional[typing.Callable]
        self._loop = asyncio.get_running_loop()
        self._hostname = ""

    def set_host_name(self, name: str) -> None:
        self._hostname = name

    async def new_link(self, linkid: str,
                       host: str = "",
                       port: int = 0) -> None:

        reader, writer = await asyncio.open_connection(host, port)

        await sending(writer, HeartbeatLetter(self._hostname, 0))
        self._links[linkid] = Link(
            linkid, host, port, reader, writer, Link.ACTIVE)

        self._loop.create_task(self._active_link(reader, writer, linkid))

    async def rebuild_link(self, link: Link) -> None:

        while True:
            try:
                reader, writer = await asyncio.open_connection(
                    link.host, link.port)
                break
            except ConnectionRefusedError:
                link.state = Link.DISCONNECTED
                await asyncio.sleep(1)

        link.reader = reader
        link.writer = writer
        link.state = Link.CONNECTED

        self._loop.create_task(self._active_link(reader, writer, link.ident))

    async def _active_link(self, reader: asyncio.StreamReader,
                           writer: asyncio.StreamWriter,
                           linkid: str) -> None:
        # Link Init
        try:
            first_heart_beat = HeartbeatLetter(self._hostname, 0)
            await sending(writer, first_heart_beat)

            heartbeat = await receving(reader, timeout=3)
            print(heartbeat)
        except Exception:
            self._link_rebuild_helper(linkid)

        if not isinstance(heartbeat, HeartbeatLetter):
            del self._links[linkid]
            return

        await self._manage_queue.put(heartbeat)

        link = self._links[linkid]

        while True:

            if link.state == Link.REMOVED:
                del self._links[linkid]
                break

            try:
                letter = await receving(reader)
            except (ConnectionResetError, BrokenPipeError):
                self._link_rebuild_helper(linkid)
                break

            if isinstance(letter, HeartbeatLetter):
                await self._manage_queue.put(letter)
            else:
                if self.msg_callback is None:
                    raise LINK_MSG_CALLBACK_NOT_EXISTS()
                await self.msg_callback(letter)

    def _link_rebuild_helper(self, linkid: str) -> None:
        link = self._links[linkid]
        link.state = Link.RECONNECTING

        self._loop.create_task(
            delayExec(self.rebuild_link(link), secs=1))

    def delete_link(self, linkid: str) -> None:
        self._links[linkid].state = Link.REMOVED

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

            self._links[ident] = Link(
                ident, "", 0, reader, writer, Link.PASSIVE)
        else:
            return

        # Send the first heartbaeat to manage queue
        await self._manage_queue.put(first_heart_beat)

        while True:
            try:
                letter = await receving(reader)
            except Exception:
                del self._links[ident]

            if isinstance(letter, HeartbeatLetter):
                await self._manage_queue.put(letter)
            else:
                if self.msg_callback is None:
                    raise LINK_MSG_CALLBACK_NOT_EXISTS()
                await self.msg_callback(letter)

    def exists(self, linkid: str) -> bool:
        return linkid in self._links

    async def sendLetter(self, linkid: str, letter: Letter) -> None:
        try:
            link = self._links[linkid]
        except KeyError:
            raise LINK_NOT_EXISTS(linkid)

        await sending(link.writer, letter)

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
        self._linker = Linker()

    def listen(self, lisId: str, host: str, port: int) -> None:
        self._linker.new_listen(lisId, host, port)

    def open_connection(self, linkId, host: str, port: int) -> None:
        self._linker.new_link(linkId, host, port)

    def set_msg_callback(self, cb: typing.Callable) -> None:
        self._linker.msg_callback = cb

    def init(self) -> None:
        # msg_callback of linker must be setup before
        # start otherwise another component is unable
        # to get letter from connector.
        assert(self._linker.msg_callback is not None)
        self._linker.start()

    async def sendLetter(self, letter: Letter) -> None:
        linkid = letter.getHeader('linkid')
        if linkid == "":
            return

        await self._linker.sendLetter(linkid, letter)


class LINK_MSG_CALLBACK_NOT_EXISTS(Exception):

    def __str__(self) -> str:
        return "Link message callback is not seted"


class LINK_NOT_EXISTS(Exception):

    def __init__(self, linkid) -> None:
        self._linkid = linkid

    def __str__(self) -> str:
        return "Link " + self._linkid + " not exist"
