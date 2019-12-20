# connector.py
#
# Maintain connection with workers

from threading import Lock
from manager.misc.type import *
from manager.misc.worker import Worker

from threading import Thread
import socket

from manager.misc.components import Components

class WorkerRoom(Thread):

    def __init__(self, host, port):
        Thread.__init__(self)

        # This lock is use to protect __workers
        # while add or remove workers from it
        # Note: This lock will not protect access to a worker object
        self.lock = Lock()

        # Chooise map is for quickly searching purpose
        self.__workers = {}
        self.numOfWorkers = 0

        # Collection of method to be run after a worker is accept
        # by WorkerRoom
        # Every entry in hooks is a pair such that (f:func, args:List)
        self.hooks = []

        self.__host = host
        self.__port = port

        self.sock = None

    def run(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((self.__host, self.__port))
        self.sock.listen(5)

        # Cause not only accept a new worker in a loop also
        # to do another works, such as discover an disconnected
        # worker and remove it
        self.sock.settimeout(1)

        while True:
            self.waitWorker()

    def waitWorker(self):
        try:
            (workersocket, address) = self.sock.accept()

            acceptedWorker = Worker(workersocket)

            if acceptedWorker == None:
                return None

            print("New worker Arrived:" + acceptedWorker.getIdent())

            self.addWorker(acceptedWorker)
            list(map(lambda hook: hook[0](acceptedWorker, hook[1]), self.hooks))

        except:
            return None

    def hookRegister(self, hook):
        self.hooks.append(hook)

    def markDisconnected(self, ident):
        pass

    def getWorkerViaFd(self, fd):
        pass

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
