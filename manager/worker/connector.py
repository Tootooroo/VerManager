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
import platform
import traceback
import manager.worker.configs as cfg

from manager.basic.letter import BinaryLetter, sending_sock
from socket import socket
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from manager.worker.channel import ChannelReceiver
from manager.basic.letter import receving, sending, HeartbeatLetter, Letter,\
    PropLetter


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
        self.last = datetime.utcnow()
        self.host = host
        self.port = port

    def hb_timeer_udpate(self) -> None:
        self.last = datetime.utcnow()

    def hb_timer_diff(self) -> int:
        return (datetime.utcnow() - self.last).seconds


class Linker:

    def __init__(self) -> None:
        self._links = {}  # type: typing.Dict[str, Link]
        self._links_passive = {}  # type: typing.Dict[str, Link]
        self._lis = {}  # type: typing.Dict[str, typing.Any]
        self.msg_callback = None  # type: typing.Optional[typing.Callable]
        self._loop = asyncio.get_running_loop()
        self._lock = asyncio.Lock()

        assert(cfg.config is not None)
        self._hostname = cfg.config.getConfig('WORKER_NAME')
        if self._hostname == "":
            self._hostname = platform.node()
        self.channel_data = None  # type: typing.Optional[typing.Dict]

    def set_host_name(self, name: str) -> None:
        self._hostname = name

    async def new_link(self, linkid: str,
                       host: str = "",
                       port: int = 0) -> None:

        reader, writer = await asyncio.open_connection(host, port)

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

        link.hbCount = 0
        link.reader = reader
        link.writer = writer
        link.state = Link.CONNECTED

        self._loop.create_task(self._active_link(reader, writer, link.ident))

    async def _active_link(self, reader: asyncio.StreamReader,
                           writer: asyncio.StreamWriter,
                           linkid: str) -> None:
        assert(cfg.config is not None)

        link = self._links[linkid]

        # Link Init
        proc = 0
        max_proc_job = cfg.config.getConfig('MAX_TASK_CAN_PROC')
        role = cfg.config.getConfig('ROLE')

        try:
            # Send Property LEtter
            await sending(writer, PropLetter(
                self._hostname, max_proc_job, str(proc), role))

            # Send First heartbeat
            await sending(writer, HeartbeatLetter(self._hostname, 0))
            # Update timer
            link.hb_timeer_udpate()

        except (ConnectionError, BrokenPipeError):
            # Wait a while
            await asyncio.sleep(1)
            self._link_rebuild_helper(linkid)
            # Exit
            return

        while True:
            if link.state == Link.REMOVED:
                del self._links[linkid]
                break

            try:
                if self._heartbeat_check(link) is False:
                    raise ConnectionError()
                letter = await receving(reader, timeout=3)
            except (ConnectionError, ConnectionResetError, BrokenPipeError):
                # Wait a while
                await asyncio.sleep(1)
                self._link_rebuild_helper(linkid)
                # Exit
                return
            except asyncio.exceptions.TimeoutError:
                continue

            if isinstance(letter, HeartbeatLetter):
                link.hb_timeer_udpate()
                await self.heartbeat_proc_active(linkid, letter)
            else:
                if self.msg_callback is None:
                    raise LINK_MSG_CALLBACK_NOT_EXISTS()
                await self.msg_callback(letter)

    def _link_rebuild_helper(self, linkid: str) -> None:
        link = self._links[linkid]
        link.writer.close()
        link.state = Link.RECONNECTING

        self._loop.create_task(self.rebuild_link(link))

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
            propLetter = await receving(reader, timeout=3)
        except asyncio.exceptions.TimeoutError:
            writer.close()
            return

        if isinstance(propLetter, PropLetter):
            ident = propLetter.getIdent()
            if ident in self._links:
                return

            self._links_passive[ident] = Link(
                ident, "", 0, reader, writer, Link.PASSIVE)
        else:
            return

        while True:
            try:
                letter = await receving(reader)
            except Exception:
                writer.close()
                del self._links_passive[ident]
                break

            if isinstance(letter, HeartbeatLetter):
                await self.heartbeat_proc_passive(letter)
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

        await sending(link.writer, letter, lock=self._lock)

    @staticmethod
    def _do_send_file(sock: socket, linkid: str,
                      path: str, tid: str,
                      version: str, fileName: str) -> bool:
        try:
            file = open(path, "rb")

            for line in file:
                line_bin = BinaryLetter(
                    tid=tid, bStr=line, parent=version,
                    fileName=fileName)
                line_bin.setHeader("linkid", linkid)
                sending_sock(sock, line_bin)

            end_bin = BinaryLetter(tid=tid, bStr=b"",
                                   parent=version, fileName=fileName)
            end_bin.setHeader("linkid", linkid)
            sending_sock(sock, end_bin)
        except Exception:
            import traceback
            traceback.print_exc()
            return False

        return True

    async def sendfile(self, linkid: str, tid: str, path: str,
                       version: str, fileName: str) -> bool:
        if linkid not in self._links:
            raise LINK_NOT_EXISTS(linkid)

        link = self._links[linkid]
        sock = link.writer.transport.get_extra_info('socket')
        e = ProcessPoolExecutor(max_workers=1)
        return await self._loop.run_in_executor(
            e, self._do_send_file,
            sock._sock, linkid, path, tid, version, fileName)

    async def heartbeat_proc_active(self, linkid: str,
                                    heartbeat: HeartbeatLetter) -> None:
        if linkid not in self._links:
            return

        link = self._links[linkid]
        seq = heartbeat.getSeq()

        if link.hbCount != seq:
            return

        link.hbCount += 1
        self._loop.create_task(self._next_heartbeat(link, 5))

    async def heartbeat_proc_passive(self, heartbeat: HeartbeatLetter) -> None:
        ident = heartbeat.getIdent()
        if ident not in self._links_passive:
            return

        link = self._links_passive[ident]
        seq = heartbeat.getSeq()

        if link.hbCount != seq:
            return

        link.hbCount += 1

        heartbeat.setIdent(self._hostname)
        await sending(link.writer, heartbeat)

    async def _next_heartbeat(self, link: Link, delay: int) -> None:
        await asyncio.sleep(delay)

        hb = HeartbeatLetter(self._hostname, link.hbCount)
        try:
            await sending(link.writer, hb)
        except ConnectionError:
            # Just return
            # that link will be rebuild while timer
            # timeout in wrost situation.
            return
        except Exception:
            traceback.print_exc()

    def _heartbeat_check(self, link: Link) -> bool:
        return link.hb_timer_diff() < 30

    def link_state(self, linkid: str) -> int:
        try:
            return self._links[linkid].state
        except KeyError:
            return Link.REMOVED


class Connector(ChannelReceiver):

    def __init__(self) -> None:
        ChannelReceiver.__init__(self)

        self._linker = Linker()
        self._letter_Q = asyncio.Queue(128)  # type: asyncio.Queue[Letter]

    async def listen(self, lisId: str, host: str, port: int) -> None:
        await self._linker.new_listen(lisId, host, port)

    async def open_connection(self, linkId, host: str, port: int) -> None:
        await self._linker.new_link(linkId, host, port)

    def close(self, linkId: str) -> None:
        self._linker.delete_link(linkId)

    def set_msg_callback(self, cb: typing.Callable) -> None:
        self._linker.msg_callback = cb

    def queue(self) -> typing.Optional[asyncio.Queue]:
        return self._letter_Q

    async def sendLetter(self, letter: Letter, timeout=None) -> None:
        linkid = letter.getHeader('linkid')
        if linkid == "":
            raise LINK_ID_NOT_FOUND()

        await asyncio.wait_for(
            self._linker.sendLetter(linkid, letter), timeout=timeout)

    async def sendFile(self, linkid: str, tid: str, path: str,
                       version: str, fileName: str) -> bool:
        return await self._linker.sendfile(
            linkid, tid, path, version, fileName)

    def link_state(self, linkid: str) -> int:
        return self._linker.link_state(linkid)

    async def update(self, uid: str) -> None:
        # Do nothing
        return None


class LINK_ID_NOT_FOUND(Exception):

    def __str__(self) -> str:
        return "Link id is not found"


class LINK_MSG_CALLBACK_NOT_EXISTS(Exception):

    def __str__(self) -> str:
        return "Link message callback is not seted"


class LINK_NOT_EXISTS(Exception):

    def __init__(self, linkid) -> None:
        self._linkid = linkid

    def __str__(self) -> str:
        return "Link " + self._linkid + " not exist"
