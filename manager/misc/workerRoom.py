# connector.py
#
# Maintain connection with workers

from threading import Lock
from manager.misc.type import *
from manager.misc.worker import Worker

from threading import Thread
from queue import Queue, Empty
import socket

from manager.misc.components import Components

class WorkerMaintainer(Thread):

    def __init__(self, workerRoom):
        Thread.__init__(self)
        self.workerRoom = workerRoom

    def run(self):
        while True:
            self.workerRoom.maintain()

class WorkerRoom(Thread):

    WAITING_INTERVAL = 300

    EVENT_CONNECTED = 0
    EVENT_DISCONNECTED = 1
    EVENT_WAITING = 2

    def __init__(self, host, port):
        Thread.__init__(self)

        # This lock is use to protect __workers
        # while add or remove workers from it
        # Note: This lock will not protect access to a worker object
        self.lock = Lock()

        # Chooise map is for quickly searching purpose
        self.__workers = {}
        self.__workers_waiting = {}
        self.numOfWorkers = 0

        self.__eventQueue = Queue(256)

        # Collection of method to be run after a worker is accept
        # by WorkerRoom
        # Every entry in hooks is a pair such that (f:func, args:List)
        self.hooks = []

        self.waitingStateHooks = []
        self.disconnStateHooks = []

        self.__host = host
        self.__port = port

        self.sock = None

    def run(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((self.__host, self.__port))
        self.sock.listen(5)

        # Spawn a thread which respond to worker maintain
        maintainer = WorkerMaintainer(self)
        maintainer.start()

        while True:
            (workersocket, address) = self.sock.accept()

            acceptedWorker = Worker(workersocket)

            if acceptedWorker == None:
                return None

            print("New worker Arrived:" + acceptedWorker.getIdent())

            self.addWorker(acceptedWorker)
            list(map(lambda hook: hook[0](acceptedWorker, hook[1]), self.hooks))


    # While eventlistener notify that a worker is disconnected
    # just change it's state into waiting wait <waiting_interval>
    # minutes if the workers is still disconnected then change
    # it's state into disconnected and wait several seconds
    # and remove from WorkerRoom
    #
    # Caution: Calling of hooks is necessary while a worker's state is changed
    def maintain(self):

        while True:
            self.__waiting_worker_processing(self.__workers_waiting)

            try:
                (eventType, ident) = self.__eventQueue.get(timeout=1)
            except Empty:
                continue

            worker = self.getWorker(ident)
            print("Worker " + worker.getIdent() + " is disconnected...Waiting")

            if eventType == WorkerRoom.EVENT_DISCONNECTED:
                # Update worker's counter
                worker.setState(Worker.STATE_WAITING)

                worker.counterReset()
                worker.counterSync()

                self.__worker_waiting.append(worker)

                list(map(lambda hook: hook[0](worker, hook[1]), self.waitingStateHooks))

    # Update workers's counter and deal with workers
    # thoses out of date
    def __waiting_worker_processing(self, workers):
        if len(workers) == 0:
            return None

        outOfTime = list(filter(lambda w: w.waitCounter() > 300, workers))

        for worker in outOfTime:
            worker.setState(Worker.STATE_OFFLINE)
            list(map(lambda hook: hook[0](worker, hook[1]), self.disconnStateHooks))

        list(map(lambda w: self.removeWorker(w.getIdent()), outOfTime))


    def __waiting_worker_update(worker):
        pass

    def hookRegister(self, hook):
        self.hooks.append(hook)

    def waitingHookRegister(self, hook):
        self.hooks.append(hook)

    def disconnHookRegister(self, hook):
        self.hooks.append(hook)

    def notifyEvent(self, eventType, ident):
        self.__eventQueue.put((eventType, ident))

    def getWorkerViaFd(self, fd):
        workers = list(self.__workers.values())
        theWorker = list(filter(lambda w: w.sock.fileno() == fd, workers))

        if len(theWorker) == 0:
            return None

        return theWorker[0]

    def getWorker(self, ident):
        with self.lock:
            if not ident in self.__workers:
                return None

            return self.__workers[ident]

    # Type of condRtn is condRtn([worker1, worker2, worker3, ...])
    def getWorkerWithCond(self, condRtn):
        with self.lock:
            workerList = list(self.__workers.values())
            return condRtn(workerList)

    def addWorker(self, w):
        ident = w.getIdent()
        with self.lock:
            if ident in self.__workers:
                return Error

            self.__workers[ident] = w
            self.numOfWorkers += 1
            return Ok

    def isExists(self, ident):
        if ident in self.__workers:
            return True
        else:
            return False

    def getNumOfWorkers(self):
        return self.numOfWorkers

    def removeWorker(self, ident):
        with self.lock:
            if not ident in self.__workers:
                return Error

            del self.__workers [ident]
            self.numOfWorkers -= 1

        return Ok
