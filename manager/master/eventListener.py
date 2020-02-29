# EventListener

import socket
import zipfile
import select

from typing import *

from manager.master.exceptions import *
from manager.basic.mmanager import ModuleDaemon
from manager.master.worker import Worker, Task
from manager.basic.type import *
from manager.master.workerRoom import WorkerRoom
from manager.basic.letter import Letter

import traceback

M_NAME = "EventListener"

# Constant
letterLog = "letterLog"

Handler = Callable[['EventListener', Letter], None]

class EventListener(ModuleDaemon):

    def __init__(self, workerRoom: WorkerRoom, inst:Any) -> None:
        global letterLog, M_NAME

        self.__sInst = inst

        ModuleDaemon.__init__(self, M_NAME)
        self.entries = select.poll()
        self.workers = workerRoom
        self.numOfEntries = 0

        # Handler in handlers should be unique
        self.handlers = {} # type: Dict[str, List[Handler]]

        # {tid:fd}
        self.taskResultFdSet = {} # type: Dict[str, BinaryIO]

    def getModule(self, m:str) -> Any:
        return self.__sInst.getModule(m)

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

    def fdUnregister(self, ident: str) -> None:
        workers = self.getModule('WorkerRoom')
        worker = workers.getWorker()

        if not worker is None:
            sock = worker.sock

        self.entries.unregister(sock.fileno())

    def addWorker(self, worker: Worker) -> State:
        ident = worker.getIdent()
        isNotExists = not self.workers.isExists(ident)

        if isNotExists:
            self.workers.addWorker(worker)
            # Register socket into entries
            sock = worker.sock
            self.entries.register(sock.fileno(), select.POLLIN)
            self.entries.register(sock.fileno(), select.POLLERR)
            return Ok

        return Error

    def removeWorker(self, ident) -> State:
        worker = self.workers.getWorker(ident)

        if not worker is None:
            # Unregister the socket from poll object
            self.entries.unregister(worker.sockGet())
            # remove worker
            self.workers.removeWorker(ident)
            return Ok

        return Error

    def Acceptor(self, letter: Letter) -> None:
        # Check letter's type
        event = letter.type_

        if event == Letter.NewTask or event == Letter.TaskCancel:
            return None

        handlers = self.handlers[event]
        list(map(lambda h: h(self, letter), handlers)) # type: ignore

    def run(self) -> None:
        global letterLog
        logger = self.__sInst.getModule('Logger')

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
                    self.workers.notifyEventFd(WorkerRoom.EVENT_DISCONNECTED, fd)

                    self.entries.unregister(fd)
                    continue

                if letter != None:
                    self.Acceptor(letter)

# Hooks
def workerRegister(worker:Worker, args:Any) -> None:
    eventListener = args[0]
    eventListener.fdRegister(worker)
