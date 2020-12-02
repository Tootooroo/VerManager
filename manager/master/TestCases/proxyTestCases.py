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
import typing as T
import client.client as C
from manager.master.proxy import Proxy
from client.messages import Message
from manager.master.msgCell import MsgWrapper, MsgSource


class ClientFake(C.Client):

    def __init__(self, ident: str) -> None:
        C.Client.__init__(self, ident)
        self.msgs = []  # type:  T.List[Message]

    async def notify(self, message: Message) -> None:
        self.msgs.append(message)


class SourceTrivial(MsgSource):

    async def gen_msg(self) -> T.Optional[Message]:
        return Message("Test", {})


class ProxyTestCases(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self) -> None:
        self.sut = Proxy(10)

    async def test_Proxy_RealTimeNotify(self) -> None:
        # Setup
        client = ClientFake("Fake")
        C.clients["Fake"] = client

        source = SourceTrivial("SRC1")
        self.sut.add_msg_source("Test", source, {})

        # Exercise
        self.sut.start()
        await asyncio.sleep(1)

        msg = Message("Test", {})
        source.real_time_msg(msg, {"is_broadcast": "ON"})
        await asyncio.sleep(1)

        # Verify
        self.assertTrue(len(client.msgs) == 1)
        self.assertEqual(msg, client.msgs[0])


class MsgWrapperTestCases(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self) -> None:
        self.msg = msg = Message("T", {})
        self.sut = MsgWrapper(msg)

    async def test_MsgWrapper_GetMsg(self) -> None:
        # Exercise and Verify
        self.assertEqual(self.msg, self.sut.get_msg())

    async def test_MsgWrapper_addConfig(self) -> None:
        key_on = "cfg_on"

        # Exercise
        self.sut.add_config(key_on, "val")

        # Verify
        self.assertEqual("val", self.sut.get_config(key_on))
