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
import unittest

from manager.basic.util import delayExec
from manager.basic.letter import receving, PropLetter
from manager.worker.server import Server
from manager.basic.info import Info
from manager.basic.virtuals.virtualServer import VirtualServer


async def coroStop(coro):
    await asyncio.sleep(2)
    coro.cancel()


class VirtServer(VirtualServer):

    def __init__(self, ident: str, addr: str, port: int) -> None:
        VirtualServer.__init__(self, ident, addr, port)
        self.callback = None

    async def conn_callback(
            self,
            r: asyncio.StreamReader,
            w: asyncio.StreamWriter) -> None:

        await self.callback(r, w)
        await self.stop()


async def checkPropLetter(r, w):
    letter = await receving(r)
    if isinstance(letter, PropLetter):
        max = letter.getMax()
        proc = letter.getProc()

        assert("0" == max)
        assert("0" == proc)


class ServerTestCases(unittest.TestCase):

    async def setUp_coro(self) -> None:
        info = Info("./config_test.yaml")
        self.server = Server("127.0.0.1", 30000, info)
        self.vir_server = VirtServer("Server", "127.0.0.1", 30000)

    def test_connect(self) -> None:
        # Exercise
        async def testing() -> None:
            await self.setUp_coro()
            self.vir_server.callback = checkPropLetter

            await asyncio.gather(
                self.vir_server.start(),
                delayExec(self.server.connect(), secs=1))

        asyncio.run(testing())

        # Verify
        self.assertEqual(
            Server.STATE_CONNECTED,
            self.server.getStatus()
        )

    def test_heartbeat(self) -> None:
        pass
