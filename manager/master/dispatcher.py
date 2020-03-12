# dispatcher.py
#
# Responsbility to version generation works dispatch,
# load-balance, queue supported

import time

M_NAME = "Dispatcher"

from typing import *
from functools import reduce

from threading import Lock, Event
from manager.master.build import Build, BuildSet
from manager.basic.mmanager import ModuleDaemon
from manager.master.worker import Worker
from manager.master.postElection import Role_Listener, Role_Provider
from manager.basic.info import Info, M_NAME as INFO_M_NAME
from manager.basic.type import *
from manager.master.task import TaskState, Task, SuperTask, SingleTask, PostTask
from manager.basic.type import *

from manager.master.workerRoom import WorkerRoom

from datetime import datetime

from manager.master.logger import Logger

from manager.master.logger import M_NAME as LOGGER_M_NAME

class Dispatcher(ModuleDaemon):

    def __init__(self, workerRoom:WorkerRoom, inst:Any) -> None:
        global M_NAME
        ModuleDaemon.__init__(self, M_NAME)

        self.__sInst = inst

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
        if isinstance(task, SuperTask):
            return self.__dispatchSuperTask(task)

        ret = self.__do_dispatch(task)
        if ret is True:
            self.__tasks[task.id()] = task
            return ret

        return False

    def __do_dispatch(self, task: Task) -> bool:
        # First to find a acceptable worker
        # if found then assign task to the worker
        # and __tasks otherwise append to taskWait
        cond = viaOverhead
        workers = [] # type: List[Worker]

        if isinstance(task, PostTask):
            cond = theListener

        workers = self.__workers.getWorkerWithCond(cond)

        # No workers satisfiy the condition.
        if workers == []:
            print("Unable to accept")
            return False

        try:
            workers[0].do(task)
        except:
            return False

        return True

    def __dispatchSuperTask(self, task: SuperTask) -> bool:
        ret = True
        subTasks = task.getChildren()

        for sub in subTasks:
            if not sub.isPrepare():
                continue

            do_ret = self.__do_dispatch(sub)

            if do_ret is False:
                ret = False
            else:
                sub.stateChange(Task.STATE_IN_PROC)

        if ret is True:
            task.stateChange(Task.STATE_IN_PROC)

        return ret

    def dispatch(self, task: Task) -> bool:
        if task.id() in self.__tasks:
            task = self.__tasks[task.id()]
            task.refs += 1

            return True

        # Bind task with a build or buildSet
        task = self.__bind(task)

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
            task.stateChange(Task.STATE_PREPARE)
            del self.__tasks [taskId]

        with self.dispatchLock:
            if self.__do_dispatch(task) is False:
                self.taskWait.insert(0, task)
                self.__tasks[task.id()] = task
                self.taskEvent.set()

        return True

    def __bind(self, task:Task) -> Task:
        if not task.isBindWithBuild():
            # To check taht whether the task bind with
            # a build or BuildSet. If not bind just to
            # bind one with it.
            info = self.__sInst.getModule(INFO_M_NAME) # type: Info

            try:
                build = Build(task.vsn ,info.getConfig("Build"))
                if isinstance(build, Build):
                    task.setBuild(build)
            except:
                pass

            try:
                buildSet = BuildSet(info.getConfig("BuildSet"))
                if isinstance(buildSet, BuildSet):
                    task.setBuild(buildSet)
            except:
                pass
            task = task.transform()

        return task


    # Dispatcher thread is response to assign task in queue which name is taskWait
    def run(self) -> None:
        logger = self.__sInst.getModule(LOGGER_M_NAME)

        if not logger is None:
            logger.log_register("dispatcher")

        counter = 0


        while True:
            # Remove oudated tasks
            self.__taskAging()

            # Is there any task in taskWait queue
            # fixme: need to setup a timeout value
            isArrived = self.taskEvent.wait(2)
            if not isArrived or counter % 5 == 0:
                if counter > 10000:
                    counter = 0

                counter += 1
                continue

            Logger.putLog(logger, "dispatcher", "Task arrived")

            # Is there any workers acceptable
            workers = self.__workers.getWorkerWithCond(acceptableWorkers)

            if workers == []:
                Logger.putLog(logger, "dispatcher", "No acceptable worker")
                time.sleep(0.1)
                continue

            task = self.taskWait.pop()

            Logger.putLog(logger, "dispatcher", "Dispatch task: " + task.id())

            if not self.__dispatch(task):
                Logger.putLog(logger, "dispatcher",
                              "Dispatcher task " + task.id() + " failed. Reappend")

                self.taskWait.append(task)

            if len(self.taskWait) == 0:
                self.taskEvent.clear()

    def __taskAging(self) -> None:
        tasks = list(self.__tasks.values())

        current = datetime.utcnow()
        cond_long = lambda t: (current - t.last()).seconds > 60

        # For a task that refs reduce to 0 do aging instance otherwise wait 1 min
        tasks_outdated = list(filter(lambda t: True if t.refs == 0 else cond_long(t), tasks))

        idents_outdated = list(map(lambda t: t.id(), tasks_outdated))

        for ident in idents_outdated:
            if not ident in self.__tasks:
                continue

            t = self.__tasks[ident]

            # Task in proc or prepare status
            # will not be aging even thought
            # their counter is out of date.
            if t.isProc() or t.isPrepare():
                continue

            del self.__tasks [ident]

    # Cancel a task identified by taskId
    # and taskId is unique
    def cancel(self, taskId: str) -> None:
        pass

    # Cancel all tasks processing on a worker
    def cancelOnWorker(self, wId: str) -> None:
        pass

    def removeTask(self, taskId: str) -> None:
        if taskId in self.__tasks:
            del self.__tasks [taskId]

    def getTask(self, taskId:str) -> Optional[Task]:
        if not taskId in self.__tasks:
            return None
        return self.__tasks[taskId]

    # Use to get result of task
    # after the call of this method task will be
    # remove from __tasks
    def retrive(self, taskId: str) -> Optional[str]:
        if not taskId in self.__tasks:
            return None

        task = self.__tasks[taskId]
        if not task.isFinished():
            return None

        if task.refs > 0:
            task.refs -= 1

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

    def taskLastUpdate(self, taskId: str) -> None:
        if not taskId in self.__tasks:
            return None

        task = self.__tasks[taskId]
        task.lastUpdate()

    def addWorkers(self, w: Worker) -> State:
        return self.__workers.addWorker(w)

    def removeWorkers(self, ident: str) -> State:
        return self.__workers.removeWorker(ident)


# Hooks will be registered into WorkerRoom

def workerLost_redispatch(w: Worker, args:Any) -> None:
    tasks = w.inProcTasks()
    dispatcher = args[0]
    workerRoom = args[1]

    for t in tasks:
        assert(isinstance(t, SingleTask) or isinstance(t, PostTask))

        # Not to redispatch tasks that need post-processing.
        if w.role is Role_Listener and t.isAChild():
            parent = t.getParent()
            assert(parent is not None)
            parent.toState_force(Task.STATE_FAILURE)

        dispatcher.redispatch(t)

    workers = workerRoom.getWorkerWithCond(lambda ws: ws)

    # Remove all tasks in failure state.
    if w.role is Role_Listener:
        for w in workers:
            w.removeTaskWithCond(lambda t: t.isFailure())

# Misc

# Method to get an online worker which
# with lowest overhead of all online workerd
def viaOverhead(workers: List[Worker]) -> List[Worker]:
    # Filter out workers which is not in online status or not able to accept
    onlineWorkers = acceptableWorkers(workers)

    if onlineWorkers == []:
        return []

    # Find out the worker with lowest overhead on a collection of online acceptable workers
    f = lambda acc, w: acc if acc.numOfTaskProc() <= w.numOfTaskProc() else w
    theWorker = reduce(f, onlineWorkers)

    return [theWorker]

def acceptableWorkers(workers: List[Worker]) -> List[Worker]:
    f_online_acceptable = lambda w: w.isOnline() and w.isAbleToAccept()
    return list(filter(lambda w: f_online_acceptable(w), workers))

def theListener(workers: List[Worker]) -> List[Worker]:
    return list(filter(lambda w: w.role == Role_Listener, workers))
