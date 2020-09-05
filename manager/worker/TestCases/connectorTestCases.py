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
import manager.worker.TestCases.misc.linker as misc

from manager.worker.connector import Linker


class LinkerTestCases(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self) -> None:
        self.linker = Linker()

    async def test_Linker_NewLink_Connect(self) -> None:
        """
        Linker try to open a connection to VirtualServer.
        If success a link should be spawned.
        """
        # Setup
        vir_server = misc.VirtualServer("127.0.0.1", 8888)
        vir_server.start()
        await asyncio.sleep(0.1)

        # Exercise
        await self.linker.new_link("Server", "127.0.0.1", 8888)
        await asyncio.sleep(0.1)

        # Verify
        self.assertTrue(self.linker.exists("Server"))

    async def test_Linker_NewLink_Accept(self) -> None:
        """
        Linker listen on 8889 and VirtualWworker will
        connect to it. There should be a link exists.
        """

        # Setup
        vir_worker = misc.VirtualWorker("VirtualWorker", "127.0.0.1", 8889)

        # Exercise
        await self.linker.new_listen("lis1", "127.0.0.1", 8889)
        await asyncio.sleep(0.1)
        vir_worker.start()
        await asyncio.sleep(0.1)

        # Verify
        self.assertTrue(self.linker.exists("VirtualWorker"))

    async def test_Linker_Heartbeat_PASSIVE(self) -> None:
        """
        Maintain a link between a VirtualWorker and Linker
        """

        # Setup
        vir_worker = misc.VirtualWorker_Heartbeat_ACTIVE(
            "Worker", "127.0.0.1", 8899)

        # Exercise
        self.linker.start()
        await self.linker.new_listen("lis1", "127.0.0.1", 8899)
        await asyncio.sleep(0.1)

        vir_worker.start()
        await asyncio.sleep(3)

        # Verify
        self.assertGreater(vir_worker._hbCount, 1)

    async def test_Linker_Heartbeat_Active(self) -> None:
        """ Maintain a linke of a passive """

        # Setup
        vir_worker = misc.VirtualWorker_Heartbeat_Passive("Worker",
                                                          "127.0.0.1", 8810)

        # Exercise
        vir_worker.start()
        await asyncio.sleep(3)

        self.linker.start()
        await self.linker.new_link("Worker", "127.0.0.1", 8810)
        await asyncio.sleep(0.1)

        # Verify
        self.assertGreater(vir_worker._hbCount, 1)
