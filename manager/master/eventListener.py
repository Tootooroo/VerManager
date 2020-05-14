# EventListener

import socket
import select

from typing import Callable, Any, Dict, BinaryIO, List
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

        self.entries = select.poll()
        self.numOfEntries = 0

        # Handler in handlers should be unique
        self.handlers = {}  # type: Dict[str, List[Handler]]

        # {tid:fd}
        self.taskResultFdSet = {}  # type: Dict[str, BinaryIO]

    def begin(self) -> None:
        return None

    def cleanup(self) -> None:
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

    def fdRegister(self, worker: Worker) -> None:
        sock = worker.sock
        self.entries.register(sock.fileno(), select.POLLIN)

    def fdUnregister(self, fd) -> None:
        self.entries.unregister(fd)

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
