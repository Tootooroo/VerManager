# dispatcher.py
#
# Responsbility to version generation works dispatch,
# load-balance, queue supported

import time

import manager.misc.components as Components

from typing import *
from functools import reduce

from threading import Thread, Lock, Event
from manager.misc.worker import Worker
from manager.misc.basic.type import *
from manager.misc.task import TaskState, Task
from manager.misc.basic.type import *

class Dispatcher(Thread):

    def __init__(self, workerRoom) -> None:
        Thread.__init__(self)

        # A queue contain a collection of tasks
        self.taskWait = [] # type: List[Task]

        # An Event to indicate that there is some task in taskWait queue
        self.taskEvent = Event()

        self.dispatchLock = Lock()

        # For query purposes
        # { taskId : Task }
        self.__tasks = {} # type: Dict[str, Task]

        self.__workers = workerRoom

        # To protect __workers while add or remove
        # worker is happen during search on __workers
        self.__workerLock = Lock()
        self.__numOfWorkers = 0

    # Dispatch a task to a worker of
    # all by overhead of workers
    #
    # return True if task is assign successful otherwise return False
    def __dispatch(self, task: Task) -> bool:

        if task.id() in self.__tasks and task.taskState() == Task.STATE_IN_PROC:
            return True

        # First to find a acceptable worker
        # if found then assign task to the worker
        # and __tasks otherwise append to taskWai
        theWorker = self.__workers.getWorkerWithCond(viaOverhead)

        if theWorker != None:
            try:
                theWorker.do(task)
            except:
                return False

            print("push " + task.id() + " into tasks")
            self.__tasks[task.id()] = task
            return True

        return False

    def dispatch(self, task: Task) -> bool:
        with self.dispatchLock:
            if self.__dispatch(task) == False:
                # fixme: Queue may full while inserting
                self.taskWait.insert(0, task)
                self.__tasks[task.id()] = task
                self.taskEvent.set()

            return True

    def redispatch(self, task: Task) -> bool:
        taskId = task.id()
        if taskId in self.__tasks:
            del self.__tasks [taskId]
        return self.dispatch(task)

    # Dispatcher thread is response to assign task in queue which name is taskWait
    def run(self) -> None:
        logger = Components.logger;

        logger.log_register("dispatcher")

        while True:

            # Is there any task in taskWait queue
            self.taskEvent.wait()
            logger.log_put("dispatcher", "Task arrived")

            # Is there any workers acceptable
            workers = self.__workers.getWorkerWithCond(acceptableWorkers)
            if workers == []:
                logger.log_put("dispatcher", "No acceptable worker")
                time.sleep(5)
                continue

            task = self.taskWait.pop()

            logger.log_put("dispatcher", "Dispatch task: " + task.id())

            if not self.__dispatch(task):
                self.taskWait.append(task)

            if len(self.taskWait) == 0:
                self.taskEvent.clear()

    # Cancel a task identified by taskId
    # and taskId is unique
    def cancel(self, taskId: str) -> None:
        pass

    # Cancel all tasks processing on a worker
    def cancelOnWorker(self, wId: str) -> None:
        pass

    # Use to get result of task
    # after the call of this method task will be
    # remove from __tasks
    def retrive(self, taskId: str) -> Optional[str]:
        if not taskId in self.__tasks:
            return None

        task = self.__tasks[taskId]
        if not task.isFinished():
            return None

        del self.__tasks [taskId]

        return task.data

    def taskState(self, taskId: str) -> int:
        if not taskId in self.__tasks:
            return Error

        task = self.__tasks[taskId]
        return task.taskState()

    def isTaskExists(self, taskId: str) -> bool:
        return taskId in self.__tasks

    def __isTask(self, taskId: str, state: Callable) -> bool:
        if not taskId in self.__tasks:
            return False

        task = self.__tasks[taskId]
        return state(task)

    def isTaskPrepare(self, taskId: str) -> bool:
        return self.__isTask(taskId, lambda t: t.taskState() == Task.STATE_PREPARE)

    def isTaskInProc(self, taskId: str) -> bool:
        return self.__isTask(taskId, lambda t: t.taskState() == Task.STATE_IN_PROC)

    def isTaskFailure(self, taskId: str) -> bool:
        return self.__isTask(taskId, lambda t: t.taskState() == Task.STATE_FAILURE)

    def isTaskFinished(self, taskId: str) -> bool:
        return self.__isTask(taskId, lambda t: t.taskState() == Task.STATE_FINISHED)

    def addWorkers(self, w: Worker) -> State:
        return self.__workers.addWorker(w)

    def removeWorkers(self, ident: str) -> State:
        return self.__workers.removeWorker(ident)


# Hooks will be registered into WorkerRoom
def workerLost_redispatch(w: Worker, d: Dispatcher) -> None:
    tasks = w.inProcTasks()
    list(map(lambda task: d.redispatch(task), tasks))

# Misc

# Method to get an online worker which
# with lowest overhead of all online workerd
def viaOverhead(workers: List[Worker]) -> Optional[Worker]:
    # Filter out workers which is not in online status or not able to accept
    onlineWorkers = acceptableWorkers(workers)

    if onlineWorkers == []:
        return None

    # Find out the worker with lowest overhead on a collection of online acceptable workers
    f = lambda acc, w: acc if acc.numOfTaskProc() <= w.numOfTaskProc() else w
    return reduce(f, onlineWorkers)

def acceptableWorkers(workers: List[Worker]) -> List[Worker]:
    f_online_acceptable = lambda w: w.isOnline() and w.isAbleToAccept()
    return list(filter(lambda w: f_online_acceptable(w), workers))
