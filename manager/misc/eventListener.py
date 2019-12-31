import socket
import select
from threading import Thread

from typing import *
from manager.misc.exceptions import *

from manager.misc.worker import Worker, Task
from manager.misc.basic.type import *
from manager.misc.workerRoom import WorkerRoom
from manager.misc.basic.letter import Letter

import manager.misc.components as Components

import traceback

# Constant
letterLog = "letterLog"

Handler = Callable[['EventListener', Letter], None]

class EventListener(Thread):

    def __init__(self, workerRoom: WorkerRoom) -> None:
        global letterLog

        Thread.__init__(self)
        self.entries = select.poll()
        self.workers = workerRoom
        self.numOfEntries = 0

        # Handler in handlers should be unique
        self.handlers = {} # type: Dict[str, Handler]

        # {tid:fd}
        self.taskResultFdSet = {} # type: Dict[str, BinaryIO]

    def registerEvent(self, eventType: str, handler: Handler) -> None:
        if eventType in self.handlers:
            return None

        self.handlers[eventType] = handler

    def unregisterEvent(self, eventType: str) -> None:
        if not eventType in self.handlers:
            return None

        del self.handlers [eventType]

    def fdRegister(self, worker: Worker) -> None:
        sock = worker.sock
        self.entries.register(sock.fileno(), select.POLLIN)

    def fdUnregister(self, ident: str) -> None:
        worker = self.getWorker(ident)

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

    def getWorker(self, ident: str) -> Optional[Worker]:
        return self.workers.getWorker(ident)

    def Acceptor(self, letter: Letter) -> None:
        # Check letter's type
        event = letter.type_

        if event == Letter.NewTask or event == Letter.TaskCancel:
            return None

        handler = self.handlers[event]
        handler(self, letter)

    def run(self) -> None:
        global letterLog
        logger = Components.logger

        if Components.logger is None:
            raise COMPONENTS_LOG_NOT_INIT
        else:
            # Register log files
            Components.logger.log_register(letterLog)


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
                        logger.log_put((letterLog, "Letter is NoneType"))
                        continue

                    if not letter.validity():
                        logger.log_put((letterLog, "Receive invalid letter " + letter.toString()))
                        continue

                    logger.log_put((letterLog, "Receive letter " + letter.toString()))

                except:
                    traceback.print_exc()
                    # Notify workerRoom an worker is disconnected
                    worker = self.workers.getWorkerViaFd(fd)

                    if not worker is None:
                        ident = worker.getIdent()
                        logger.log_put((letterLog, "Worker " + ident + " is disconnected"))
                        self.workers.notifyEvent(WorkerRoom.EVENT_DISCONNECTED, ident)
                    else:
                        logger.log_put((letterLog, "workers.getWorkerViaFd() return None"))

                    self.entries.unregister(fd)
                    continue

                if letter != None:
                    self.Acceptor(letter)

# Hooks
def workerRegister(worker: Worker, args: Any) -> None:
    eventListener = args[0]
    eventListener.fdRegister(worker)

# Handlers definitions

# Handler to process response of NewTask request
def responseHandler(eventListener: EventListener, letter: Letter) -> None:
    # Should verify the letter's format
    ident = letter.getHeader('ident')
    taskId = letter.getHeader('tid')

    state = int(letter.getContent('state'))

    worker = eventListener.getWorker(ident)

    if not worker is None:
        task = worker.searchTask(taskId)

    if not task is None and Task.isValidState(state):
        # Do some operation after finished such as close file description
        # of received binary
        if state == Task.STATE_FINISHED:
            print("Finished")
            # Store result to the target position specified in configuration file

            # Send email to notify that task id done

            task.setData("http://127.0.0.1:8000/static/" + task.id())
            fdSet = eventListener.taskResultFdSet
            fdSet[taskId].close()
            del fdSet [taskId]

        print(ident + " change to state " + str(state))
        task.stateChange(state)

def binaryHandler(eventListener: EventListener, letter: Letter) -> None:
    fdSet = eventListener.taskResultFdSet
    tid = letter.getHeader('tid')

    # This is the first binary letter of the task correspond to the
    # received tid just open a file and store the relation into fdSet
    if not tid in fdSet:
        newFd = open("./data/" + tid, "wb")
        fdSet[tid] = newFd

    fd = fdSet[tid]
    content = letter.getContent('content')

    if isinstance(content, str):
        return None

    fd.write(content)

def logHandler(eventListener: EventListener, letter: Letter) -> None:
    logger = Components.logger

    logId = letter.getHeader('logId')
    logMsg = letter.getContent('logMsg')

    logger.log_put((logId, logMsg))

def logRegisterhandler(eventListener: EventListener, letter: Letter) -> None:
    logger = Components.logger

    logId = letter.getHeader('logId')

    logger.log_register(logId)
