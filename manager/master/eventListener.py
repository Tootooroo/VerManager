# EventListener

import unittest
import asyncio

from collections import namedtuple
from typing import Callable, Any, Dict, List, Optional, cast
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

Handler = Callable[['Entry.EntryEnv', Letter], None]


class Entry:
    """
    An entry describe connection with a worker
    and logics that deal with event received
    from the worker.
    """
    EntryEnv = namedtuple('EntryEnv', 'eventListener handlers')

    def __init__(self, worker, env: EntryEnv) -> None:
        self._worker = worker
        self._env = env
        self._hbCount = 0
        self._stop = False

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

        hbEvent.setIdent("Master")
        await self._worker.sendLetter(hbEvent)

    async def eventProc(self) -> None:
        event = await self._worker.waitResponse(timeout=1)  \
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
            self._env.handlers[type](self._env, event)
        except Exception:
            pass

    async def monitor(self) -> None:
        while True:
            if self._stop:
                return None

            await self.eventProc()


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

    async def begin(self) -> None:
        return None

    async def cleanup(self) -> None:
        return None

    async def stop(self) -> None:
        return None

    def needStop(self) -> bool:
        return False

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

    def Acceptor(self, letter: Letter) -> None:
        # Check letter's type
        event = letter.type_

        if event == Letter.NewTask or event == Letter.TaskCancel:
            return None

        handlers = self.handlers[event]
        list(map(lambda h: h(self, letter), handlers))  # type: ignore

    def event_log(self, msg: str) -> None:
        self.notify(EventListener.NOTIFY_LOG, (letterLog, msg))

    def register(self, worker: Worker) -> None:
        if worker not in self.regWorkers:
            self.regWorkers.append(worker)

    def registered(self) -> List[Worker]:
        return self.regWorkers

    def remove(self, ident: str) -> None:
        self.regWorkers = \
            [w for w in self.regWorkers if w.getIdent() != ident]

    async def _entryDispatch(self) -> bool:
        return True

    async def run(self) -> None:
        pass


def workerRegister(eventListener: EventListener,
                   worker: Worker) -> None:
    return None


# Entry TestCases
class WorkerStubEntry(WorkerStub):

    def __init__(self, ident) -> None:
        WorkerStub.__init__(self, ident)
        self.q = None  # type: Optional[asyncio.Queue]

    async def sendEvent(self, letter: Letter) -> Optional[Letter]:
        if self.q is None:
            return None
        return await self.q.put(letter)

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
            return await asyncio.wait_for(self.rq.get(), timeout=1)
        except asyncio.exceptions.TimeoutError:
            return None


class EntryTestCases(unittest.TestCase):

    def setUp(self) -> None:
        env = Entry.EntryEnv(None, {})  # type: Entry.EntryEnv
        self.entry = Entry(WorkerStubEntry("w1"), env)

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

        async def sendHeartbeat(worker: WorkerMockEntry):
            heartbeat = HeartbeatLetter(worker.ident, 0)
            await worker.sendEvent(heartbeat)
            await asyncio.sleep(1)
            letter = await worker.waitMsgFromServer()

            # Verify
            self.assertEqual("Master", letter.getIdent())  # type: ignore

            self.entry.stop()

        # Exercise
        async def doTest() -> None:
            worker = cast(WorkerMockEntry, self.entry.getWorker())
            worker.q = asyncio.Queue(10)
            worker.rq = asyncio.Queue(10)

            await asyncio.gather(
                sendHeartbeat(worker),
                self.entry.eventProc()
            )

        asyncio.run(doTest())

        # Verify
        self.assertEqual(1, self.entry._hbCount)


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
        self.eventL = EventListener(None)

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

    def test_EventListener_HeartBeat(self) -> None:
        # Setup
        w1 = WorkerMockHeartBeat("w1")
        w2 = WorkerMockHeartBeat("w2")
        self.eventL.register(w1)
        self.eventL.register(w2)

        # Exercise
        async def doTest():
            w1.q = asyncio.Queue(10)
            w2.q = asyncio.Queue(10)

            asyncio.gather(
                runEventL(self.eventL),
                stopEventLDelay(self.eventL),
                w1.heartbeatProc()
            )
        asyncio.run(doTest())

        # Verify
        self.assertEqual(3, w1.heartbeatCount)
        self.assertEqual(3, w2.heartbeatCount)

    def test_EventListener_handleEvent(self) -> None:
        # Setup
        w1 = WorkerMockEvent("w1")
        w2 = WorkerMockEvent("w2")
        self.eventL.register(w1)
        self.eventL.register(w2)

        hDone = False

        def handler(e, l):
            nonlocal hDone
            hDone = True

        self.eventL.registerEvent("H", handler)

        # Exercise
        async def doTest():
            w1.q = asyncio.Queue(10)
            w2.q = asyncio.Queue(10)

            asyncio.gather(
                runEventL(self.eventL),
                stopEventLDelay(self.eventL),
                w1.eventProc()
            )
        asyncio.run(doTest())

        # Verify
        self.assertTrue(hDone)
