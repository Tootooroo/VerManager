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
from manager.worker.linker import Linker
from manager.worker.link import HBLink
from manager.basic.letter import Letter
from manager.basic.info import Info
import manager.worker.configs as share


async def trivial_dispatch_proc(letter: Letter) -> None:
    return None


async def trivial_cb(r: asyncio.StreamReader, w: asyncio.StreamWriter) -> None:
    link = HBLink("A", "127.0.0.1", 7777, r, w, {"hostname": "hostB"})
    link.start()
    link.setDispatchProc(trivial_dispatch_proc)

    await asyncio.sleep(10)


class LinkerTestCases(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self) -> None:
        share.config = Info("./manager/worker/TestCases/misc/config.yaml")
        self.sut = Linker(trivial_dispatch_proc)
        self.loop = asyncio.get_running_loop()

    async def test_Linker_CreateListener(self) -> None:
        pass

    async def test_Linker_CreateLink(self) -> None:
        """
        Start an server then create a link to the server.
        """
        # Setup
        server = await asyncio.start_server(
            trivial_cb, host="127.0.0.1", port=7777
        )
        self.loop.create_task(server.serve_forever())

        # Exercise
        await self.sut.createLink("Link1", "127.0.0.1", 7777)

        # Verify
        self.assertTrue(self.sut.exists("Link1"))

    async def test_Linker_DeleteLink(self) -> None:
        """
        Create a link then delete it.
        """
        server = await asyncio.start_server(
            trivial_cb, host="127.0.0.1", port=7777
        )
        self.loop.create_task(server.serve_forever())

        # Exercise
        await self.sut.createLink("Link1", "127.0.0.1", 7777)
        self.assertTrue(self.sut.exists("Link1"))
        self.sut.deleteLink("Link1")

        # Verify
        self.assertFalse(self.sut.exists("Link1"))

    async def test_Linker_SendOnLink(self) -> None:
        """
        Create a link then send data on it
        """
        pass
