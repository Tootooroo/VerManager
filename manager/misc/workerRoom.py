# connector.py
#
# Maintain connection with workers

import socket

from threading import Lock
from manager.misc.basic.type import *
from manager.misc.worker import Worker, WorkerInitFailed

from threading import Thread
from queue import Queue, Empty

from manager.misc.util import spawnThread

from typing import *

import manager.misc.components as Components

# Type alias
EVENT_TYPE = int
hookTuple = Tuple[Callable[[Worker, Any], None], Any]
filterFunc = Callable[[List[Worker]], Optional[Worker]]

# Constant
wrLog = "wrLog"

class WorkerRoom(Thread):

    WAITING_INTERVAL = 300

    EVENT_CONNECTED = 0
    EVENT_DISCONNECTED = 1
    EVENT_WAITING = 2

    def __init__(self, host:str, port:int) -> None:
        Thread.__init__(self)

        # This lock is use to protect __workers
        # while add or remove workers from it
        # Note: This lock will not protect access to a worker object
        self.lock = Lock()

        # Lock to prevent race between Waiting thread and maintain thread
        self.syncLock = Lock()

        # __workers is a collection of workers in online state
        self.__workers = {}         # type: Dict[str, Worker]

        # __workers_waiting is a collection of workers in waiting state
        # if a worker which in this collection exceed WAIT limit it will
        # be removed
        self.__workers_waiting = {} # type: Dict[str, Worker]
        self.numOfWorkers = 0

        self.__eventQueue = Queue(256) # type: Queue

        # Collection of methods to be run after a worker is accepted by WorkerRoom
        self.hooks = [] # type: List[hookTuple]

        self.waitingStateHooks = [] # type: List[hookTuple]
        self.disconnStateHooks = [] # type: List[hookTuple]

        self.__host = host
        self.__port = port

    def run(self) -> None:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((self.__host, self.__port))
        self.sock.listen(5)

        # Spawn a thread which respond to worker maintain
        maintainer = spawnThread(lambda wr: wr.maintain(), self)

        global wrLog
        logger = Components.logger
        logger.log_register(wrLog)

        while True:
            (workersocket, address) = self.sock.accept()
            logger.log_put(wrLog, "A new connection(" + str(address) + ") has been accepted")

            workersocket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            workersocket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 10)
            workersocket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 1)
            workersocket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)
            logger.log_put(wrLog, "Socket options set up")

            try:
                acceptedWorker = Worker(workersocket)
                acceptedWorker.active()

                ident = acceptedWorker.getIdent()

                logger.log_put(wrLog, "Worker " + ident + " initialized success")

            except WorkerInitFailed:
                logger.log_put(wrLog, "Worker initialize faile and close the socket")
                workersocket.shutdown(socket.SHUT_RDWR)
                continue

            if self.isExists(ident):
                logger.log_put(wrLog, "Worker " + ident + " is already exist in WorkerRoom")
                continue

            self.syncLock.acquire()

            if ident in self.__workers_waiting:
                # fixme: socket of workerInWait is broken need to
                # change to acceptedWorker
                workerInWait = self.__workers_waiting[ident]

                workerInWait.sockSet(acceptedWorker.sockGet())

                self.addWorker(workerInWait)
                del self.__workers_waiting [ident]

                list(map(lambda hook: hook[0](workerInWait, hook[1]), self.hooks)) # type: ignore

                self.syncLock.release()

                continue

            self.syncLock.release()

            self.addWorker(acceptedWorker)
            list(map(lambda hook: hook[0](acceptedWorker, hook[1]), self.hooks)) # type: ignore


    # While eventlistener notify that a worker is disconnected
    # just change it's state into waiting wait <waiting_interval>
    # minutes if the workers is still disconnected then change
    # it's state into disconnected and wait several seconds
    # and remove from WorkerRoom
    #
    # Caution: Calling of hooks is necessary while a worker's state is changed
    def maintain(self) -> None:
        logger = Components.logger

        while True:
            self.__waiting_worker_processing(self.__workers_waiting)

            try:
                (eventType, index) = self.__eventQueue.get(timeout=1)
            except Empty:
                continue

            if isinstance(index, str):
                # Via Worker Ident
                worker = self.getWorker(index)
            elif isinstance(index, int):
                # Via Fd in worker
                worker = self.getWorkerViaFd(index)

            if worker is None:
                continue

            ident = worker.getIdent()

            if eventType == WorkerRoom.EVENT_DISCONNECTED:
                logger.log_put(wrLog, "Worker " + ident + \
                               " is disconnected changed state into Waiting")

                # Update worker's counter
                worker.setState(Worker.STATE_WAITING)
                worker.counterSync()

                self.removeWorker(ident)

                with self.syncLock:
                    self.__workers_waiting[ident] = worker

                list(map(lambda hook: hook[0](worker, hook[1]), self.waitingStateHooks)) # type: ignore

    # Update workers's counter and deal with workers
    # thoses out of date
    def __waiting_worker_processing(self, workers: Dict[str, Worker]) -> None:
        logger = Components.logger

        workers_list = list(workers.values())

        if len(workers) == 0:
            return None

        outOfTime = list(filter(lambda w: w.waitCounter() > 300, workers_list))

        for worker in outOfTime:
            ident = worker.getIdent()
            logger.log_put(wrLog, "Worker " + ident +\
                           " is dissconnected for a long time will be removed")
            worker.setState(Worker.STATE_OFFLINE)
            list(map(lambda hook: hook[0](worker, hook[1]), self.disconnStateHooks)) # type: ignore

        list(map(lambda w: self.removeWorker(w.getIdent()), outOfTime))

    def hookRegister(self, hook: hookTuple) -> None:
        self.hooks.append(hook)

    def waitingHookRegister(self, hook: hookTuple) -> None:
        self.hooks.append(hook)

    def disconnHookRegister(self, hook: hookTuple) -> None:
        self.hooks.append(hook)

    def notifyEvent(self, eventType: EVENT_TYPE, ident: str) -> None:
        self.__eventQueue.put((eventType, ident))

    def notifyEventFd(self, eventType: EVENT_TYPE, fd: int) -> None:
        self.__eventQueue.put((eventType, fd))

    def getWorkerViaFd(self, fd: int) -> Optional[Worker]:
        workers = list(self.__workers.values())
        theWorker = list(filter(lambda w: w.sock.fileno() == fd, workers))

        if len(theWorker) == 0:
            return None

        return theWorker[0]

    def getWorker(self, ident: str) -> Optional[Worker]:
        with self.lock:
            if not ident in self.__workers:
                return None

            return self.__workers[ident]

    def getWorkerWithCond(self, condRtn: filterFunc) -> Optional[Worker]:
        with self.lock:
            workerList = list(self.__workers.values())
            return condRtn(workerList)

    def addWorker(self, w: Worker) -> State:
        ident = w.getIdent()
        with self.lock:
            if ident in self.__workers:
                return Error

            self.__workers[ident] = w
            self.numOfWorkers += 1
            return Ok

    def isExists(self, ident: str) -> bool:
        if ident in self.__workers:
            return True
        else:
            return False

    def getNumOfWorkers(self) -> int:
        return self.numOfWorkers

    def removeWorker(self, ident: str) -> State:
        with self.lock:
            if not ident in self.__workers:
                return Error

            del self.__workers [ident]
            self.numOfWorkers -= 1

        return Ok

    # Content of dictionary:
    # { PropertyName:PropertyValue }
    # e.g { "max":0, "sock":ref, "processing":0, "inProcTask":ref, "ident":name }
    def statusOfWorker(self, ident:str) -> Dict:
        worker = self.getWorker(ident)
        return worker.status()
