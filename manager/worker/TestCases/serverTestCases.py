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
import typing

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
        self.callback = None  # type: typing.Any

    async def conn_callback(
            self,
            r: asyncio.StreamReader,
            w: asyncio.StreamWriter) -> None:

        await self.callback(r, w, self)


async def checkPropLetter(r, w, server):
    letter = await receving(r)
    if isinstance(letter, PropLetter):
        max = letter.getMax()
        proc = letter.getProc()

        assert("0" == max)
        assert("0" == proc)
        await server.stop()


async def checkPropLetter_(r, w: asyncio.StreamWriter, server):
    if not hasattr(server, "count"):
        server.count = 0

    letter = await receving(r)
    if isinstance(letter, PropLetter):
        max = letter.getMax()
        proc = letter.getProc()

        assert("0" == max)
        assert("0" == proc)
    else:
        assert(False)

    if server.count > 0:
        await server.stop()

    server.count += 1
    w.close()


async def tryReconnect(server: Server) -> None:
    await server.connect()
    server.setStatus(Server.STATE_TRANSFER)

    for i in range(5):
        if server._writer is None:
            continue

        await asyncio.sleep(0.1)

        await server.transfer(PropLetter("", "", ""))
        try:
            await server.transfer_step()
        except (ConnectionResetError, BrokenPipeError):
            await server.reconnect()


async def transferTest_ServerWork(server: Server) -> None:
    await server.connect()
    server.setStatus(Server.STATE_TRANSFER)

    # Send letter
    await server.transfer(PropLetter("W", "0", "0"))
    await server.transfer_step()

    # Recv letter
    letter = await server.waitLetter()

    if isinstance(letter, PropLetter):
        max = letter.getMax()
        proc = letter.getProc()

        assert("2" == max)
        assert("2" == proc)
    else:
        assert(False)


async def transferTest_VirtWork(r, w, server: VirtServer) -> None:

    letter = await receving(r)

    if isinstance(letter, PropLetter):
        max = letter.getMax()
        proc = letter.getProc()

        assert("0" == max)
        assert("0" == proc)
    else:
        assert(False)

    w.write(PropLetter("2", "2", "2").toBytesWithLength())
    await w.drain()

    await server.stop()


count = 0
letters = []  # type: typing.List[PropLetter]


async def transferInterruptTest_VirtWork(r, w, server: VirtServer) -> None:
    global count, letters

    await receving(r)

    while count < 30:
        count += 1

        try:
            letter = await asyncio.wait_for(receving(r), timeout=2)
        except asyncio.exceptions.TimeoutError:
            break

        assert(isinstance(letter, PropLetter))
        letters.append(letter)

        if count % 10 == 0 and count > 0:
            w.close()
            return

    # Verify
    idx = 0
    for letter in letters:
        proc = letter.getProc()
        assert(proc == str(idx))
        idx += 1

    server.stop()


class ServerTestCases(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self) -> None:
        info = Info("./config_test.yaml")
        self.server = Server("127.0.0.1", 30000, info)
        self.vir_server = VirtServer("Server", "127.0.0.1", 30000)
        self.loop = asyncio.get_running_loop()

    async def test_Server_connect(self) -> None:
        # Exercise
        self.vir_server.callback = checkPropLetter
        await asyncio.gather(
            self.vir_server.start(),
            delayExec(self.server.connect(), secs=1))

        # Verify
        self.assertEqual(
            Server.STATE_CONNECTED,
            self.server.getStatus()
        )

    async def test_Server_reconnect(self) -> None:
        # Setup
        self.vir_server.callback = checkPropLetter_

        # Exercise
        await asyncio.gather(
            self.vir_server.start(),
            delayExec(tryReconnect(self.server), secs=1)
        )

        # Verify
        self.assertEqual(
            Server.STATE_CONNECTED,
            self.server.getStatus()
        )

    async def test_Server_transfer(self) -> None:
        # Setup
        self.vir_server.callback = transferTest_VirtWork

        # Exercise and Verify
        await asyncio.gather(
            self.vir_server.start(),
            delayExec(transferTest_ServerWork(self.server), secs=1)
        )

    @unittest.skip("Retransfer seems not possible on this layer")
    async def test_Server_transferInterrupt(self) -> None:
        # Setup
        idx = 0
        self.vir_server.callback = transferInterruptTest_VirtWork

        # Exercise

        # Start VirtualServer
        self.loop.create_task(self.vir_server.start())

        await asyncio.sleep(0.5)
        await self.server.connect()
        self.server.setStatus(Server.STATE_TRANSFER)
        while idx < 30:
            await asyncio.sleep(0.1)
            await self.server.transfer(
                PropLetter("", "", str(idx))
            )

            try:
                await self.server.transfer_step()
            except (ConnectionResetError, BrokenPipeError):
                await self.server.reconnect()
                self.server.setStatus(Server.STATE_TRANSFER)
            idx += 1

        while self.loop.is_running():
            await asyncio.sleep(1)
