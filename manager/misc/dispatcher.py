# dispatcher.py
#
# Responsbility to version generation works dispatch,
# load-balance, queue supported

import typing

from threading import Thread, Lock, Event
from manager.misc.worker import Task, Worker
from manager.misc.type import *

class Dispatcher(Thread):

    def __init__(self, sock, workerRoom):
        Thread.__init__(self)

        # A queue contain a collection of tasks
        self.taskWait = []
        # An Event to indicate that there is some task in taskWait queue
        self.taskEvent = Event()

        # Master socket used to waiting for worker
        # request messages
        self.sock = sock

        # For query purposes
        # { taskId : Task }
        self.__tasks = {}

        self.__workers = workerRoom

        # To protect __workers while add or remove
        # worker is happen during search on __workers
        self.__workerLock = Lock()
        self.__numOfWorkers = 0

    # Dispatch a task to a worker of
    # all by overhead of workers
    #
    # return True if task is assign successful otherwise return False
    def __dispatch(self, task):

        # Method to get an online worker which
        # with lowest overhead of all online workerd
        def viaOverhead(workers):
            # Filter out workers which is not in online status
            f_oneline_acceptable = lambda w: w.getState() == Worker.STATE_ONLINE and w.isAbleToAccpt()
            onlineWorkers = list(filter(lambda w: f_online_acceptable, workers))
            if onlineWorkers == []:
                return None

            # Find out the worker with lowest overhead on a collection of online acceptable workers
            f = lambda acc, w: acc if acc.numOfTaskProc() <= w.numOfTaskProc() else w
            theWorker = list(reduce(f, onlineWorkers))

            return theWorker

        # First to find a acceptable worker
        # if found then assign task to the worker
        # and __tasks otherwise append to taskWai
        theWorker = self.__workers.getWorkerWithCond(viaOverhead)

        if theWorker != None:
            theWorker.do(task)
            self.__tasks[task.id()] = task
            return True

        return False

    def dispatch(self, task):
        if not self.__dispatch(task):
            self.taskWait.insert(0, task)
            self.taskEvent.set()
            return False
        return True

    # Dispatcher thread is response to assign task in queue which name is taskWait
    def run(self):
        self.taskEvent.wait()

        task = self.taskWait.pop()

        if not self.__dispatch(task):
            self.taskWait.append(task)

        if len(self.taskWait) == 0:
            self.taskEvent.clear()

    # Cancel a task identified by taskId
    # and taskId is unique
    def cancel(self, taskId):
        pass

    # Use to get result of task
    # after the call of this method task will be
    # remove from __tasks
    def retrive(self, taskId):
        if not taskId in self.__tasks:
            return None

        task = self.__tasks[taskId]
        if not task.isFinished():
            return None

        del self.__tasks [taskId]

        return task.data

    def taskState(self, taskId):
        if not taskId in self.__tasks:
            return Error

        task = self.tasks[taskId]
        return task.taskState()

    def __isTask(self, taskId, state):
        if not taskId in self.__tasks:
            return Error

        task = self.tasks[taskId]
        return state(task)

    def isTaskFProc(self, taskId):
        return self.__isTask(taskId, lambda t: t.taskState() == Task.STATE_IN_PROC)

    def isTaskFailure(self, taskId):
        return self.__isTask(taskId, lambda t: t.taskState() == Task.STATE_FAILURE)

    def isTaskFinished(self, taskId):
        return self.__isTask(taskId, lambda t: t.taskState() == Task.STATE_FINISHED)

    def addWorkers(self, w):
        return self.__workers.addWorker(w)

    def removeWorkers(self, ident):
        return self.__workers.removeWorker(ident)
