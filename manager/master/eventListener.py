# EventListener

import unittest
import asyncio

from typing import Callable, Any, Dict, List
from manager.basic.observer import Subject, Observer
from manager.basic.mmanager import ModuleDaemon
from manager.master.worker import Worker
from manager.basic.letter import Letter

# Test imports
from manager.basic.stubs.workerStup import WorkerStub
from manager.basic.commands import Command

M_NAME = "EventListener"

# Constant
letterLog = "letterLog"

Handler = Callable[['EventListener', Letter], None]


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

    async def run(self) -> None:
        return None


def workerRegister(eventListener: EventListener,
                   worker: Worker) -> None:
    return None


# Testcases
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
        self.q = None  # type: Optional[asyncio.Queue]

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
