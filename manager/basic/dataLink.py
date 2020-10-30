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
import multiprocessing
import threading
import traceback
from collections import namedtuple
from manager.basic.letter import receving
from typing import Dict, List, Callable, Tuple, Any, \
    Optional
from asyncio import StreamReader, StreamWriter
from manager.basic.mmanager import ModuleTDaemon


M_NAME = "DATALINKER"

address = str
port = int
tag = str
arg = Any


DataLinkNotify = namedtuple("notify", "tag msg")


class DATA_LINK_NOT_EXISTS(Exception):

    def __init__(self, host: str, port: int) -> None:
        self._host = host
        self._port = port

    def __str__(self) -> str:
        return "DataLink(" + self._host + "," + str(self._port) + ")" + \
            "does not exists."


class DATA_LINK_PROTO_NOT_SUPPORT(Exception):

    def __init__(self, proto: str) -> None:
        self._proto = proto

    def __str__(self) -> str:
        return "Protocol " + self._proto + " is not support."


class NOTIFIER_IS_ALREADY_EXISTS(Exception):

    def __init__(self, tag: str) -> None:
        self._tag = tag

    def __str__(self) -> str:
        return "Notifier " + self._tag + " is already exists."


class DataLinkProcProtocol(asyncio.BaseProtocol):

    def __init__(self, processor: Callable, args: Any) -> None:
        self._processor = processor
        self._args = args

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        self._transport = transport

    def datagram_received(self, data, addr) -> None:
        self._processor(data, self._args)


class Notifier:

    def __init__(self, callback: Callable, arg: Any) -> None:
        self._cb = callback
        self._arg = arg

    def notify(self, msg: Any) -> None:
        self._cb(msg, self._arg)


class DataLink:

    TCP_DATALINK = "tcp"
    UDP_DATALINK = "udp"

    def __init__(self, host: str, port: int, protocol: str,
                 processor: Callable[[Any, Any], None],
                 args: Any, notify_q: multiprocessing.Queue) -> None:
        """
        protocol's value is TCP_DATALINK or UDP_DATALINK
        """

        self.host = host
        self.port = port
        self._proto = protocol
        self._notifyQ = notify_q

        # Processor
        self._processor = processor  # type: Callable[[Any, Any], None]
        self._args = args  # type: Any

    def start(self) -> None:
        p = multiprocessing.Process(target=self.run, args=(self._notifyQ,))
        p.start()

    def notify(self, notify: DataLinkNotify) -> None:
        self._notifyQ.put_nowait(tuple(notify))

    def run(self, notify_q: multiprocessing.Queue) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            f = getattr(self, 'create_'+self._proto+'_datalink')
        except AttributeError:
            raise DATA_LINK_PROTO_NOT_SUPPORT(self._proto)

        asyncio.run(f())

    async def create_tcp_datalink(self) -> None:
        assert(self._processor is not None)

        server = await asyncio.start_server(
            self._tcp_datalink_factory, self.host, self.port)
        async with server:
            await server.serve_forever()

    async def _tcp_datalink_factory(self, reader: StreamReader,
                                    writer: StreamWriter) -> None:
        while True:
            try:
                letter = await receving(reader)
                await self._processor(self, letter, self._args)  # type: ignore
            except Exception:
                writer.close()
                break

    async def create_udp_datalink(self) -> None:
        loop = asyncio.get_running_loop()
        transport, proto = await loop.create_datagram_endpoint(
            lambda: DataLinkProcProtocol(self._processor, self._args),
            local_addr=(self.host, self.port)
        )

        while True:
            await asyncio.sleep(3600)

        transport.close()


class DataLinker(ModuleTDaemon):

    def __init__(self) -> None:
        # Init as a Thread ModuleDaemon
        ModuleTDaemon.__init__(self, M_NAME)

        self._links = []  # type: List[DataLink]
        self._msgQueue = multiprocessing.Queue(256) \
            # type: multiprocessing.Queue[DataLinkNotify]
        self._notify_cb = {}  # type: Dict[tag, Notifier]

    def addDataLink(self, host: str, port: int, proto: str,
                    processor: Callable, args: Any) -> None:

        # No replicate.
        if self.isLinkExists(host, port):
            return None

        dl = DataLink(host, port, proto, processor, args, self._msgQueue)
        self._links.append(dl)

    def addNotify(self, tag: str, cb: Callable[[Any, Any], None], arg: Any) -> None:
        if tag in self._notify_cb:
            raise NOTIFIER_IS_ALREADY_EXISTS(tag)

        notifier = Notifier(cb, arg)
        self._notify_cb[tag] = notifier

    def isLinkExists(self, host: str, port: int) -> bool:
        match = [dl for dl in self._links if host == dl.host and port == dl.port]
        return len(match) > 0

    def start(self) -> None:
        threading.Thread.start(self)

    def is_alive(self) -> bool:
        return threading.Thread.is_alive(self)

    def run(self) -> None:
        # Start all DataLinks
        for dl in self._links:
            dl.start()

        # Deal with messages from DataLinks.
        while True:

            tag, msg = self._msgQueue.get()

            if tag not in self._notify_cb:
                continue

            try:
                self._notify_cb[tag].notify(msg)
            except Exception:
                traceback.print_exc()

    def stop(self) -> None:
        """
        DataLinker is unable to stop from external.
        """
        return

    async def begin(self) -> None:
        return

    async def cleanup(self) -> None:
        return
