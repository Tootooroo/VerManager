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
from typing import Dict, List, Callable, Tuple, Any


address = str
port = int


class UNABLE_TO_ADD_PROCESSOR_TO_NON_EXISTS_DATA_LINK(Exception):

    def __init__(self, host: str, port: int) -> None:
        self._host = host
        self._port = port


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

    def isLinkExists(self, host: str, port: int) -> None:
        return host in self._links and port in self._links[host]

    def addProcessor(self, host: str, port: int, pr: Callable, *args) -> None:
        if not self.isLinkExists(host, port):
            return None


    @staticmethod
    def start(host: str, port: int) -> None:
        p = multiprocessing.Process(
            target=lambda: asyncio.run(DataLinker().run()))
        p.start()

    async def run(self) -> None:
        server = await asyncio.start_server(
            self._dataReceive, self._host, self._port)
        async with server:
            await server.serve_forever()

    async def _dataReceive(self, reader: asyncio.StreamReader,
                           writer: asyncio.StreamWriter) -> None:
        print("Datalink Open")
        # From beginLetter the information about how to
        # manage the received file
        beginLetter = await receving(reader)
        if beginLetter is None:
            writer.close()
            return

        assert(isinstance(beginLetter, BinaryLetter))

        version = beginLetter.getParent()
        fileName = beginLetter.getFileName()

        chooser = self._storage.create(version, fileName)
        if chooser is None:
            writer.close()
            return

        while True:
            piece = await reader.read(1024)
            if piece == b"":
                break
            chooser.store(piece)

        chooser.close()
        writer.close()
