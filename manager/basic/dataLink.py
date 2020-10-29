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
from typing import Dict, List, Callable, Tuple, Any, \
    Optional


address = str
port = int


class DATA_LINK_NOT_EXISTS(Exception):

    def __init__(self, host: str, port: int) -> None:
        self._host = host
        self._port = port

    def __str__(self) -> str:
        return "DataLink(" + self._host + "," + self._port  + ")" + \
            "does not exists."


class DATA_LINK_PROTO_NOT_SUPPORT(Exception):

    def __init__(self, proto: str) -> None:
        self._proto = proto

    def __str__(self) -> str:
        return "Protocol " + self._proto + " is not support."


class DataLinkProcProtocol:

    def __init__(self, processor: Callable) -> None:
        "docstring"

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        self._transport = transport

    def datagram_received(self, data, addr) -> None:
        pass


class DataLink:

    TCP_DATALINK = "tcp"
    UDP_DATALINK = "udp"

    def __init__(self, host: str, port: int, protocol: str) -> None:
        """
        protocol's value is TCP_DATALINK or UDP_DATALINK
        """

        self._host = host
        self._port = port
        self._proto = protocol

        # Processor
        self._processor = None  # type: Optional[Callable]

    def start(self) -> None:
        loop = asyncio.get_running_loop()
        try:
            f = getattr(self, 'create_'+self._proto+'datalink')
        except AttributeError:
            raise DATA_LINK_PROTO_NOT_SUPPORT(self._proto)
        loop.create_task(f)

    async def create_tcp_datalink(self) -> None:
        assert(self._processor is not None)
        server = await asyncio.start_server(
            self._processor, self._host, self._port)
        async with server:
            await server.serve_forever()

    async def create_udp_datalink(self) -> None:
        loop = asyncio.get_running_loop()

        transport, proto = await loop.create_datagram_endpoint()


class DataLinker:

    def __init__(self) -> None:
        self._links = {}  # type: Dict[address, List[port]]
        self._data_processors = {}  \
            # type: Dict[address, Dict[port, List[Tuple[Callable, Tuple[Any]]]]]

    def addDataLink(self, host: str, port: int) -> None:
        if host not in self._links:
            self._links[host] = []
        if port not in self._links[host]:
            self._links[host].append(port)

    def isLinkExists(self, host: str, port: int) -> bool:
        return host in self._links and port in self._links[host]

    def addProcessor(self, host: str, port: int, pr: Callable, *args) -> None:
        if not self.isLinkExists(host, port):
            raise DATA_LINK_NOT_EXISTS(host, port)

    @staticmethod
    def start(host: str, port: int) -> None:
        p = multiprocessing.Process(
            target=lambda: asyncio.run(DataLinker().run()))
        p.start()

    async def run(self) -> None:

        for addr in self._links:
            processor = self._data_processors[addr]
        server = await asyncio.start_server(
            self._dataReceive, self._host, self._port)
        async with server:
            await server.serve_forever()
