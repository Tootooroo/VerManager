# dispatcher.py
#
# Responsbility to version generation works dispatch,
# load-balance, queue supported

import typing

from threading import Lock
from manager.misc.worker import Task, Worker
from manager.misc.type import *

class Dispatcher:

    def __init__(self, sock):
        Thread.__init__(self)

        # Master socket used to waiting for worker
        # request messages
        self.sock = sock

        # For query purposes
        # { taskId : Task }
        self.__tasks = {}

        # { workerIdent : Worker }
        self.__workers = {}

        # To protect __workers while add or remove
        # worker is happen during search on __workers
        self.__workerLock = Lock()
        self.__numOfWorkers = 0

    # Dispatch a task to a worker of
    # all by overhead of workers
    def dispatch(self, task):
        self.__tasks[task.id()] = task


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
        with self.__workerLock:
            self.workers[w.ident()] = w
            return Ok

    def removeWorkers(self, ident):
        with self.__workerLock:
            if ident in self.__workers:
                del self.workers [ident]
                return Ok
            return Error
