# connector.py
#
# Maintain connection with workers

from threading import Lock
from manager.misc.type import *

class WorkerRoom:

    def __init__(self):
        # This lock is use to protect __workers
        # while add or remove workers from it
        # Note: This lock will not protect access to a worker object
        self.lock = Lock()

        # Chooise map is for quickly searching purpose
        self.__workers = {}
        self.numOfWorkers = 0

    def getWorker(self, ident):
        with self.lock:
            if not ident in self.__workers:
                return None

            return self.__workers[ident]

    # Type of condRtn is condRtn([worker1, worker2, worker3, ...])
    def gerWorkerWithCond(self, condRtn):
        with self.lock:
            workerList = list(self.__workers.values())
            return condRtn(workerList)

    def addWorker(self, w):
        ident = w.getIdent()
        with self.lock:
            if ident in self.__workers:
                return Error

            self.__workers[ident] = w
            return Ok

    def isExists(self, ident):
        if ident in self.__workers:
            return True
        else:
            return False

    def removeWorker(self, ident):
        with self.lock:
            if not ident in self.__workers:
                return Error

            return self.__workers[ident]
