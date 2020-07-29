# EventListener

import unittest
import socket
import asyncio

from typing import Callable, Any, Dict, List
from manager.basic.observer import Subject, Observer
from manager.basic.mmanager import ModuleDaemon
from manager.master.worker import Worker
from manager.basic.letter import Letter, BinaryLetter

import traceback

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

    async def begin(self) -> None:
        return None

    async def cleanup(self) -> None:
        return None

    async def stop(self) -> None:
        return None

    def needStop(self) -> None:
        return None

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

    def run(self) -> None:
        global letterLog

        while True:
            # Polling every 10 seconds due to polling
            # may not affect to new worker which be
            # added after poll() is called
            readyEntries = self.entries.poll(1000)

            # Read message from socket and then transfer
            # this message into letter. Then hand the
            # letter to acceptor
            for fd, event in readyEntries:
                sock = socket.fromfd(fd, socket.AF_INET, socket.SOCK_STREAM)

                try:
                    letter = Worker.receving(sock)

                    if letter is None:
                        self.event_log("Letter is NoneType")
                        continue

                    if not letter.validity():
                        self.event_log("Receive invalid letter "
                                       + letter.toString())
                        continue
                except Exception:
                    traceback.print_exc()
                    # Notify observers that a connection is lost.
                    self.notify(EventListener.NOTIFY_LOST, fd)
                    self.entries.unregister(fd)
                    continue

                if letter is not None:
                    if not isinstance(letter, BinaryLetter):
                        self.event_log("Receive: " + letter.toString())
                    self.Acceptor(letter)


def workerRegister(eventListener: EventListener,
                   worker: Worker) -> None:
    eventListener.fdRegister(worker)


# Testcases
from manager.basic.stubs.workerStup import WorkerStub
from manager.basic.commands import Command
from manager.basic.letter import CmdResponseLetter


async def runEventL(e) -> None:
    await e.run()


async def stopEventLDelay(e) -> None:
    await e.stop()



class WorkerMockEvent(WorkerStub):
    def __init__(self, ident: str) -> None:
        WorkerStub.__init__(self, ident)
        self.q = asyncio.Queue(10)  # type: asyncio.Queue

    async def eventProc(self, l: CmdResponseLetter) -> None:
        pass


class WorkerMockHeartBeat(WorkerStub):
    def __init__(self, ident: str) -> None:
        WorkerStub.__init__(self, ident)
        self.q = asyncio.Queue(10)  # type: asyncio.Queue

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
        regWorkers= self.eventL.registered()
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
        self.assertTrue(w1 in regWorkers)
        self.assertTrue(w2 not in regWorkers)

    def test_EventListener_HeartBeat(self) -> None:
        # Setup
        w1 = WorkerMockHeartBeat("w1")
        w2 = WorkerMockHeartBeat("w2")
        self.eventL.register(w1)
        self.eventL.register(w2)

        # Exercise
        asyncio.gather(
            runEventL(self.eventL),
            stopEventLDelay(self.eventL),
            w1.heartbeatProc()
        )

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
        asyncio.gather(
            runEventL(self.eventL),
            stopEventLDelay(self.eventL),
            w1.eventProc()
        )

        # Verify
        self.assertTrue(hDone)
