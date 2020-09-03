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
import  manager.worker.TestCases.misc.linker as misc

from manager.worker.connector import Linker



class LinkerTestCases(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self) -> None:
        self.linker = Linker()

    async def test_Linker_NewLink_Connect(self) -> None:
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
        # Setup
        vir_worker = misc.VirtualWorker("127.0.0.1", 8889)
        vir_worker.start()
        await asyncio.sleep(0.1)

        # Exercise
        await self.linker.new_listen("lis1", "127.0.0.1", 8889)
