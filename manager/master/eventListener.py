# EventListener

import socket
import zipfile
import select

from typing import *

from manager.master.exceptions import *
from manager.basic.observer import Subject, Observer
from manager.basic.mmanager import ModuleDaemon
from manager.master.worker import Worker, Task
from manager.basic.type import *
from manager.basic.letter import Letter, BinaryLetter

from manager.master.logger import M_NAME as LOGGER_M_NAME

import traceback

M_NAME = "EventListener"

# Constant
letterLog = "letterLog"

Handler = Callable[['EventListener', Letter], None]

class EventListener(ModuleDaemon, Subject, Observer):

    def __init__(self, inst:Any) -> None:
        global letterLog, M_NAME

        self._sInst = inst

        # Init as module
        ModuleDaemon.__init__(self, M_NAME)

        # Init as Subject
        Subject.__init__(self, M_NAME)

        # Init as Observer
        Observer.__init__(self)

        self.entries = select.poll()
        self.numOfEntries = 0

        # Handler in handlers should be unique
        self.handlers = {} # type: Dict[str, List[Handler]]

        # {tid:fd}
        self.taskResultFdSet = {} # type: Dict[str, BinaryIO]

    def getModule(self, m:str) -> Any:
        return self._sInst.getModule(m)

    def registerEvent(self, eventType: str, handler: Handler) -> None:
        if eventType in self.handlers:
            return None

        if not eventType in self.handlers:
            self.handlers[eventType] = []

        self.handlers[eventType].append(handler)

    def unregisterEvent(self, eventType: str) -> None:
        if not eventType in self.handlers:
            return None

        del self.handlers [eventType]

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
        list(map(lambda h: h(self, letter), handlers)) # type: ignore

    def run(self) -> None:
        global letterLog
        logger = self._sInst.getModule(LOGGER_M_NAME)

        if logger is None:
            raise COMPONENTS_LOG_NOT_INIT
        else:
            # Register log files
            logger.log_register(letterLog)

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
                        logger.log_put(letterLog, "Letter is NoneType")
                        continue

                    if not letter.validity():
                        logger.log_put(letterLog, "Receive invalid letter " + letter.toString())
                        continue
                except:
                    traceback.print_exc()
                    # Notify observers that a connection is lost.
                    self.notify(fd)
                    self.entries.unregister(fd)
                    continue

                if letter != None:
                    if not isinstance(letter, BinaryLetter):
                        logger.log_put(letterLog, "Receive: " + letter.toString())
                    self.Acceptor(letter)

def workerRegister(eventListener: EventListener,
                   data:Tuple[int, Worker]) -> None:
    event, worker = data

    if event == 0:
        # A worker is Connected need to listene to it.
        eventListener.fdRegister(worker)
    else:
        return None
