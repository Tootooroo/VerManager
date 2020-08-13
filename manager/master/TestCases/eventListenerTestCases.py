# MIT License
#
# Copyright (c) 2020 Tootooroo
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import unittest
import asyncio

from typing import Optional, cast
from manager.basic.stubs.workerStup import WorkerStub
from manager.basic.letter \
    import Letter, HeartbeatLetter, CmdResponseLetter, BinaryLetter
from manager.master.eventListener import Entry, EventListener
from manager.basic.commands import Command


# Entry TestCases
class WorkerStubEntry(WorkerStub):

    def __init__(self, ident) -> None:
        WorkerStub.__init__(self, ident)
        self.q = None  # type: Optional[asyncio.Queue]

    async def sendEvent(self, letter: Letter) -> None:
        if self.q is None:
            return None
        await self.q.put(letter)

    async def waitResponse(self, timeout=None) -> Optional[Letter]:
        if self.q is None:
            return None

        try:
            return await asyncio.wait_for(self.q.get(), timeout=1)
        except asyncio.exceptions.TimeoutError:
            return None


class WorkerMockEntry(WorkerStubEntry):

    def __init__(self, ident) -> None:
        WorkerStubEntry.__init__(self, ident)
        self.rq = None  # type: Optional[asyncio.Queue]

    async def sendLetter(self, letter: Letter) -> None:
        await self.rq.put(letter)  # type: ignore

    async def waitMsgFromServer(self) -> Optional[Letter]:
        try:
            return await asyncio.wait_for(
                self.rq.get(), timeout=2)  # type: ignore
        except asyncio.exceptions.TimeoutError:
            return None

    async def sendHeartbeat(self, seq):
        heartbeat = HeartbeatLetter(self.ident, seq)
        await self.sendEvent(heartbeat)

        letter = await self.waitMsgFromServer()
        assert(letter.getIdent() == 'Master')


class EntryTestCases(unittest.TestCase):

    def setUp(self) -> None:
        env = Entry.EntryEnv(None, {})  # type: Entry.EntryEnv
        self.entry = Entry("Entry", WorkerStubEntry("w1"), env)

    def test_Entry_Exists(self) -> None:
        # Setup
        def handler1(e, letter):
            return None

        # Exercise
        self.assertTrue("H" not in self.entry._env.handlers)
        self.entry.addHandler("H", handler1)

        # Exercise and verify
        self.assertTrue("H" in self.entry._env.handlers)

    def test_Entry_addHandler(self) -> None:
        # Setup
        def handler(e, letter):
            return None

        # Exercise
        self.entry.addHandler("H", handler)

        # Verify
        self.assertTrue(self.entry.isEventExists("H"))
        self.assertEqual(handler, self.entry.getHandler("H"))

    def test_Entry_removeHandler(self) -> None:
        # Setup
        def handler(e, letter):
            return None
        self.entry.addHandler("H", handler)

        # Exercise
        self.entry.removeHandler("H")

        # Verify
        self.assertTrue(not self.entry.isEventExists("H"))

    def test_Entry_EventHandle(self) -> None:
        # Setup
        eventProced = False

        async def sendEvent(worker: WorkerStubEntry):
            event = CmdResponseLetter(
                "w1", "EVENT",
                CmdResponseLetter.STATE_FAILED, {}
            )
            await worker.sendEvent(event)

            await asyncio.sleep(1)
            self.entry.stop()

        def handler(e, letter):
            nonlocal eventProced
            eventProced = True

        self.entry.addHandler("EVENT", handler)

        # Exercise
        async def doTest() -> None:
            worker = cast(WorkerStubEntry, self.entry.getWorker())
            worker.q = asyncio.Queue(10)

            await asyncio.gather(
                sendEvent(self.entry.getWorker()),  # type: ignore
                self.entry.monitor()
            )

        asyncio.run(doTest())

        # Verify
        self.assertTrue(eventProced)

    def test_Entry_Heartbeat(self) -> None:
        # Setup
        self.entry.setWorker(WorkerMockEntry("w1"))

        async def heartbeatSend(worker):
            for i in range(10):
                await worker.sendHeartbeat(i)

            self.entry.stop()

        # Exercise
        async def doTest() -> None:
            worker = cast(WorkerMockEntry, self.entry.getWorker())
            worker.q = asyncio.Queue(10)
            worker.rq = asyncio.Queue(10)

            await asyncio.gather(
                heartbeatSend(worker),
                self.entry.monitor()
            )

        asyncio.run(doTest())

        # Verify
        self.assertEqual(10, self.entry._hbCount)

    async def eventProc(self) -> None:
        pass


class WorkerMockHeartBeat(WorkerStub):
    def __init__(self, ident: str) -> None:
        WorkerStub.__init__(self, ident)
        self.q = None   # type: Optional[asyncio.Queue]

    async def control(self, cmd: Command) -> None:
        pass

    async def heartbeatProc(self) -> None:
        pass

    def heartbeatCount(self) -> int:
        pass


class EventListenerTestCases(unittest.TestCase):

    def setUp(self) -> None:
        async def doSetUp() -> None:
            self.eventL = EventListener(None)
        asyncio.run(doSetUp())

    def test_EventListener_register(self) -> None:
        # Exercise
        w1 = WorkerStub("w1")
        self.eventL.register(w1)

        # Verify
        regWorkers = self.eventL.registered()
        self.assertTrue(w1 in regWorkers)

    def test_EventListener_remove(self) -> None:
        # Setup
        w1 = WorkerStub("w1")
        w2 = WorkerStub("w2")
        self.eventL.register(w1)
        self.eventL.register(w2)

        # Exercise
        self.eventL.remove(w1.ident)

        # Verify
        regWorkers = self.eventL.registered()
        self.assertTrue(w1 not in regWorkers)
        self.assertTrue(w2 in regWorkers)

    def test_EventListener_WorkerLost(self) -> None:
        # Setup
        worker = WorkerMockEntry("w1")

        # Exercise
        async def stopEventL() -> None:
            await asyncio.sleep(5)
            await self.eventL.stop()

        async def doTest() -> None:
            worker.q = asyncio.Queue(10)
            worker.rq = asyncio.Queue(10)
            self.eventL._regWorkerQ = asyncio.Queue(25)
            await self.eventL._regWorkerQ.put(worker)

            await asyncio.gather(self.eventL.run(), stopEventL())

        asyncio.run(doTest())

        # Verify
        self.assertEqual(0, len(self.eventL._entries))
        self.assertEqual(0, len(self.eventL.regWorkers))
