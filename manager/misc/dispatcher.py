# dispatcher.py
#
# Responsbility to version generation works dispatch,
# load-balance, queue supported

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
    def __dispatch(self, task: Task) -> Optional[bool]:

        if task.id() in self.__tasks:
            return True

        # Method to get an online worker which
        # with lowest overhead of all online workerd
        def viaOverhead(workers):
            # Filter out workers which is not in online status or not able to accept
            f_online_acceptable = lambda w: w.getState() == Worker.STATE_ONLINE and w.isAbleToAccept()
            onlineWorkers = list(filter(lambda w: f_online_acceptable, workers))

            if onlineWorkers == []:
                return None

            # Find out the worker with lowest overhead on a collection of online acceptable workers
            f = lambda acc, w: acc if acc.numOfTaskProc() <= w.numOfTaskProc() else w
            theWorker = reduce(f, onlineWorkers)

            return theWorker

        # First to find a acceptable worker
        # if found then assign task to the worker
        # and __tasks otherwise append to taskWai
        theWorker = self.__workers.getWorkerWithCond(viaOverhead)

        if theWorker != None:
            # fixme: do() may failed
            theWorker.do(task)
            print("push " + task.id() + " into tasks")
            self.__tasks[task.id()] = task
            return True

        return False

    def dispatch(self, task: Task) -> bool:
        if self.__dispatch(task) == None:
            self.taskWait.insert(0, task)
            self.taskEvent.set()
            return False
        return True

    # Dispatcher thread is response to assign task in queue which name is taskWait
    def run(self) -> None:
        self.taskEvent.wait()

        task = self.taskWait.pop()

        if not self.__dispatch(task):
            self.taskWait.append(task)

        if len(self.taskWait) == 0:
            self.taskEvent.clear()

    # Cancel a task identified by taskId
    # and taskId is unique
    def cancel(self, taskId: str) -> None:
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

    def __isTask(self, taskId: str, state: Callable) -> bool:
        if not taskId in self.__tasks:
            return False

        task = self.__tasks[taskId]
        return state(task)

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
