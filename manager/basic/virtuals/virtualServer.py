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

from manager.basic.stubs.virtualMachine import VirtualMachine


class VirtualServer(VirtualMachine):

    def __init__(self, ident: str, addr: str, port: int) -> None:
        self._ident = ident
        self._addr = addr
        self._port = port
        self._coro = None  # type: typing.Any

    @abc.abstractmethod
    async def conn_callback(
            self,
            r: asyncio.StreamReader,
            w: asyncio.StreamWriter) -> None:
        """ Callback of start_server """

    async def run(self) -> None:
        server = await asyncio.start_server(
            self.conn_callback, self._addr, self._port)

        async with server:
            await server.serve_forever()
