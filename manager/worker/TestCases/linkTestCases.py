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
from manager.worker.link import HBLink
from manager.basic.letter import Letter, PropLetter
from manager.basic.observer import Observer

letters = []


class LinkObserver(Observer):

    def __init__(self) -> None:
        Observer.__init__(self)
        self.lost = False
        self.msg = ""

    async def lost_msg(self, data) -> None:
        self.msg = data
        self.lost = True


async def d_proc(letter: Letter) -> None:
    letters.append(letter)


async def conn_arrive(r: asyncio.StreamReader, w: asyncio.StreamWriter) -> None:
    passive = HBLink("A", "127.0.0.1", 7777, r, w, {"hostname": "hostB"})
    passive._dispatch_proc = d_proc
    passive.start()

    await asyncio.sleep(60)


class HBLinkTestCases(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self) -> None:
        self._loop = asyncio.get_running_loop()

        # Begin a server, connection will transform to an HBLink
        server = await asyncio.start_server(conn_arrive, "127.0.0.1", 7777)
        self._loop.create_task(server.serve_forever())

        r, w = await asyncio.open_connection("127.0.0.1", 7777)
        self.active = HBLink(
            "B", "127.0.0.1", 7777, r, w,
            {'hostname': 'hostA'}, isActiveSide=True
        )
        self.active._dispatch_proc = d_proc

    async def test_HBLink_Connect(self) -> None:
        self.active.start()
        await asyncio.sleep(10)

        self.assertEqual(self.active.hbCount, 5)

    async def test_HBLink_SendData(self) -> None:
        self.active.start()
        await asyncio.sleep(1)

        await self.active.sendletter(PropLetter("HostA", "1", "0", "M"))
        await asyncio.sleep(1)

        self.assertTrue(isinstance(letters[0], PropLetter))

    async def test_HBLink_StopLink(self) -> None:
        # Setup
        ob = LinkObserver()
        ob.handler_install("B", ob.lost_msg)
        self.active.subscribe("LinkLost", ob)

        self.active.start()
        await asyncio.sleep(1)

        self.active.stop()
        await asyncio.sleep(3)

        try:
            await self.active.sendletter(PropLetter("HostA", "1", "0", "M"))
            self.fail("Connection should be closed")
        except ConnectionError:
            pass

        # Verify
        self.assertTrue(ob.lost is True)
        self.assertTrue(ob.msg == "B")
