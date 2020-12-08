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
from manager.master.proxy import Proxy, \
    QueryInfo, message_query
from client.messages import Message
from manager.master.msgCell import MsgWrapper, MsgSource
from manager.master.jobMaster import JobMasterMsgSrc, \
    job_to_jobInfoMsg
from manager.master.job import Job
from manager.master.task import Task


class ClientFake(C.Client):

    def __init__(self, ident: str) -> None:
        C.Client.__init__(self, ident)
        self.msgs = []  # type:  T.List[Message]
        self._reg_state = True

    async def notify(self, message: Message) -> None:
        self.msgs.append(message)

    async def query(self, q_info: QueryInfo) -> None:
        msgs = await message_query(q_info)
        if msgs is None:
            return
        self.msgs = msgs


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

    async def test_Proxy_Query(self) -> None:
        # Setup
        client1 = ClientFake("Fake1")
        C.clients["Fake1"] = client1

        source = SourceTrivial("SRC1")
        self.sut.add_msg_source("Test", source, {})

        # Exercise
        q_info = QueryInfo("Test")
        await client1.query(q_info)

        # Verify
        self.assertNotEqual([], client1.msgs)
        self.assertEqual("Test", client1.msgs[0].type)


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


class MsgSourceTestCases(unittest.IsolatedAsyncioTestCase):

    async def test_JobMasterMsgSrc_GenMsg(self) -> None:
        # Setup
        src = JobMasterMsgSrc("123")

        job1 = Job("1", "1", {})
        job1._tasks["ID"] = Task("ID", "SN", "VSN")
        src.jobs = {"job1": job1}

        # Exercise
        msg = await src.gen_msg()
        assert(msg is not None)

        # Verify
        msg_d = dict(msg)
        self.assertEqual("batch", msg_d["content"]["subtype"])
        self.assertEqual(dict(job_to_jobInfoMsg(job1)), msg_d["content"]["message"][0])
