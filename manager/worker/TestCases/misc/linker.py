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

import abc
import asyncio
import typing
from .virtualmachine import VirtualMachine
from manager.basic.letter import receving, HeartbeatLetter


class VirtualServer(VirtualMachine):

    def __init__(self, host: str, port: int) -> None:
        VirtualMachine.__init__(self, "", host, port)

    async def run(self) -> None:
        server = await asyncio.start_server(
            self.handle, self._host, self._port)

        async with server:
            await server.serve_forever()

    async def handle(self,
                     r: asyncio.StreamReader,
                     w: asyncio.StreamWriter) -> None:
        while True:

            letter = await receving(r)
            self.buff.append(letter)


class VirtualWorker(VirtualMachine):

    async def run(self) -> None:
        r, w = await asyncio.open_connection(self._host, self._port)
        w.write(
            HeartbeatLetter(self._ident, 0).toBytesWithLength())
        while True:
            await asyncio.sleep(10)


class VirtualWorker_Heartbeat(VirtualMachine):

    async def run(self) -> None:
        r, w = await asyncio.open_connection(self._host, self._port)
        w.write(
            HeartbeatLetter(self._ident, 0).toBytesWithLength())

        while True:
