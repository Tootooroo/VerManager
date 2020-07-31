# EventListener

import unittest
import asyncio

from django.utils import timezone

from collections import namedtuple
from typing import Callable, Any, Dict, List, Optional, cast, Coroutine
from manager.basic.observer import Subject, Observer
from manager.basic.mmanager import ModuleDaemon
from manager.master.worker import Worker
from manager.basic.letter import Letter

# Test imports
from manager.basic.stubs.workerStup import WorkerStub
from manager.basic.commands import Command
from manager.basic.letter import CmdResponseLetter, HeartbeatLetter

M_NAME = "EventListener"

# Constant
letterLog = "letterLog"

Handler = Callable[['Entry.EntryEnv', Letter], Coroutine[Any, Any, None]]


class Entry:
    """
    An entry describe connection with a worker
    and logics that deal with event received
    from the worker.
    """
    EntryEnv = namedtuple('EntryEnv', 'eventListener handlers')

    def __init__(self, ident: str, worker, env: EntryEnv) -> None:
        self._ident = ident
        self._worker = worker
        self._env = env
        self._hbCount = 0
        self._hbTimer = timezone.now()
        self._hbTimerLimit = 3
        self._stop = False

    def getIdent(self) -> str:
        return self._ident

    def setWorker(self, worker: Worker) -> None:
        self._worker = worker

    def getWorker(self) -> Worker:
        return self._worker

    def addHandler(self, eventType: str, h: Handler) -> bool:
        if eventType in self._env.handlers:
            return False

        self._env.handlers[eventType] = h
        return True

    def removeHandler(self, eventType: str) -> None:
        del self._env.handlers[eventType]

    def getHandler(self, eventType) -> Optional[Handler]:
        if eventType in self._env.handlers:
            return self._env.handlers[eventType]
        else:
            return None

    def isEventExists(self, eventType: str) -> bool:
        return eventType in self._env.handlers

    def stop(self) -> None:
        self._stop = True

    async def _heartbeatProc(self, hbEvent: HeartbeatLetter) -> None:
        seq = hbEvent.getSeq()

        if seq != self._hbCount:
            return None

        self._hbCount += 1
        self._hbTimer = timezone.now()

        hbEvent.setIdent("Master")
        await self._worker.sendLetter(hbEvent)

    def isHeartbeatTimeout(self, current) -> bool:
        interval = (current - self._hbTimer).seconds
        return interval >= self._hbTimerLimit

    async def _heartbeatMaintain(self) -> None:
        current = timezone.now()
        eventL = self._env.eventListener  # type: EventListener
        ident = self._worker.getIdent()

        if self.isHeartbeatTimeout(current):
            await eventL.notify(eventL.NOTIFY_LOST, ident)
            eventL.remove(ident)
            eventL.removeEntry(ident)
            self.stop()

    async def eventProc(self) -> None:
        event = await self._worker.waitResponse(timeout=2)  \
            # type: Optional[CmdResponseLetter]
        if event is None:
            return None

        if isinstance(event, HeartbeatLetter):
            await self._heartbeatProc(event)
            return None

        type = event.getType()

        try:
            # eventProc must not throw any of exceptions
            # if exceptions is catch from event handlers
            # need to log into logfile.
            await self._env.handlers[type](self._env, event)
        except Exception:
            pass

    async def monitor(self) -> None:
        while True:
            if self._stop:
                return None

            await self.eventProc()
            await self._heartbeatMaintain()


class EventListener(ModuleDaemon, Subject, Observer):

    NOTIFY_LOG = "log"
    NOTIFY_LOST = "lost"

    def __init__(self, inst: Any) -> None:
        global letterLog, M_NAME

        self._sInst = inst

        # Init as module
        ModuleDaemon.__init__(self, M_NAME)

        # Init as Subject
        Subject.__init__(self, M_NAME)
        self.addType(self.NOTIFY_LOG)
        self.addType(self.NOTIFY_LOST)

        # Init as Observer
        Observer.__init__(self)

        # Handler in handlers should be unique
        self.handlers = {}  # type: Dict[str, List[Handler]]

        # Registered Workers
        self.regWorkers = []  # type: List[Worker]

        self._regWorkerQ = asyncio.Queue(25)  # type: asyncio.Queue[Worker]

        # Entries
        self._entries = {}  # type: Dict[str, Entry]
        self._stop = False

    async def begin(self) -> None:
        return None

    async def cleanup(self) -> None:
        return None

    async def stop(self) -> None:
        self._stop = True

    async def _doStop(self) -> None:
        for ident in self._entries:
            self.stopEntry(ident)

    def needStop(self) -> bool:
        return self._stop

    def getModule(self, m: str) -> Any:
        return self._sInst.getModule(m)

    def registerEvent(self, eventType: str, handler: Handler) -> None:
        if eventType in self.handlers:
            return None

        if eventType not in self.handlers:
            self.handlers[eventType] = []

        self.handlers[eventType].append(handler)

    def unregisterEvent(self, eventType: str) -> None:
        if eventType not in self.handlers:
            return None

        del self.handlers[eventType]

    def event_log(self, msg: str) -> None:
        self.notify(EventListener.NOTIFY_LOG, (letterLog, msg))

    def register(self, worker: Worker) -> None:
        if worker not in self.regWorkers:
            self.regWorkers.append(worker)

    def registered(self) -> List[Worker]:
        workerOfEntries = [e.getWorker() for e in self._entries.values()]
        return self.regWorkers + workerOfEntries

    def remove(self, ident: str) -> None:
        self.regWorkers = \
            [w for w in self.regWorkers if w.getIdent() != ident]

    def addEntry(self, entry: Entry) -> None:
        ident = entry.getIdent()

        if ident not in self._entries:
            self._entries[ident] = entry

    def removeEntry(self, ident: str) -> None:
        if ident in self._entries:
            del self._entries[ident]

    def stopEntry(self, ident: str) -> None:
        if ident in self._entries:
            self._entries[ident].stop()

    async def _attachEntry(self, entry: Entry) -> None:
        loop = asyncio.get_event_loop()
        loop.create_task(entry.monitor())

    async def run(self) -> None:
        while True:

            if self.needStop():
                await self._doStop()
                return None

            try:
                w = await asyncio.wait_for(
                    self._regWorkerQ.get(),
                    timeout=2
                )
            except asyncio.exceptions.TimeoutError:
                continue

            if w.getIdent() in self._entries:
                continue

            entryEnv = Entry.EntryEnv(self, self.handlers)
            entry = Entry(w.getIdent(), w, entryEnv)

            self.addEntry(entry)
            await self._attachEntry(entry)

    async def workerRegister(self, worker: Worker) -> None:
        if worker in self.registered():
            return None

        self.register(worker)
        await self._regWorkerQ.put(worker)


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
        def handler1(e, l):
            return None

        # Exercise
        self.assertTrue("H" not in self.entry._env.handlers)
        self.entry.addHandler("H", handler1)

        # Exercise and verify
        self.assertTrue("H" in self.entry._env.handlers)

    def test_Entry_addHandler(self) -> None:
        # Setup
        def handler(e, l):
            return None

        # Exercise
        self.entry.addHandler("H", handler)

        # Verify
        self.assertTrue(self.entry.isEventExists("H"))
        self.assertEqual(handler, self.entry.getHandler("H"))

    def test_Entry_removeHandler(self) -> None:
        # Setup
        def handler(e, l):
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

        def handler(e, l):
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


# EventListener TestCases
async def runEventL(e) -> None:
    await e.run()


async def stopEventLDelay(e) -> None:
    await e.stop()


class WorkerMockEvent(WorkerStub):
    def __init__(self, ident: str) -> None:
        WorkerStub.__init__(self, ident)
        self.q = None  # type: Optional[asyncio.Queue]

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
