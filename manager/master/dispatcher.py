# dispatcher.py
#
# Responsbility to task dispatch
# Support for load-balance, queue supported, aging.

import time
import traceback

M_NAME = "Dispatcher"

from typing import *
from functools import reduce
from datetime import datetime

from threading import Lock, Event
from manager.basic.observer import Subject, Observer
from manager.master.build import Build, BuildSet
from manager.basic.mmanager import ModuleDaemon
from manager.master.worker import Worker
from manager.master.postElection import Role_Listener, Role_Provider
from manager.basic.info import Info, M_NAME as INFO_M_NAME
from manager.basic.type import *
from manager.master.task import TaskState, Task, SuperTask, SingleTask, PostTask, TaskType
from manager.basic.type import *
from manager.master.logger import Logger, M_NAME as LOGGER_M_NAME
from manager.master.taskTracker import TaskTracker, M_NAME as TRACKER_M_NAME
from manager.master.workerRoom import WorkerRoom

class Dispatcher(ModuleDaemon, Subject, Observer):

    def __init__(self, workerRoom:WorkerRoom, inst:Any) -> None:
        global M_NAME

        ModuleDaemon.__init__(self, M_NAME)

        Subject.__init__(self, M_NAME)

        Observer.__init__(self)

        self._sInst = inst

        # A queue contain a collection of tasks
        self.taskWait = [] # type: List[Task]

        # An Event to indicate that there is some task in taskWait queue
        self.taskEvent = Event()

        self.dispatchLock = Lock()

        taskTracker = inst.getModule(TRACKER_M_NAME) # type: Optional[TaskTracker]
        assert(taskTracker is not None)
        self._taskTracker = taskTracker

        self._workers = workerRoom

        # To protect _workers while add or remove
        # worker is happen during search on _workers
        self._workerLock = Lock()
        self._numOfWorkers = 0

        self._logger = None # type: Optional[Logger]

    def _dispatch_logging(self, msg:str) -> None:
        if self._logger is None:
            self._logger = self._sInst.getModule(LOGGER_M_NAME)
            self._logger.log_register("dispatcher")

            if self._logger is None:
                return None

        Logger.putLog(self._logger, "dispatcher", msg)

    # Dispatch a task to a worker of
    # all by overhead of workers
    #
    # return True if task is assign successful otherwise return False
    def _dispatch(self, task: Task) -> bool:
        if isinstance(task, SuperTask):
            self._dispatch_logging("Task " + task.id() + " is a SuperTask.")
            return self._dispatchSuperTask(task)

        ret = self._do_dispatch(task)
        if ret is True:
            self._taskTracker.track(task)
            return ret

        return False

    def _do_dispatch(self, task: Task) -> bool:

        # First to find a acceptable worker
        # if found then assign task to the worker
        # and _tasks otherwise append to taskWait
        cond = viaOverhead
        workers = [] # type: List[Worker]

        if isinstance(task, PostTask):
            cond = theListener

        workers = self._workers.getWorkerWithCond(cond)

        # No workers satisfiy the condition.
        if workers == []:
            self._dispatch_logging("Task " + task.id() +
                                    " dispatch failed: No available worker")
            return False

        try:
            worker = workers[0]
            self._taskTracker.onWorker(task.id(), worker)

            worker.do(task)
        except:
            self._dispatch_logging("Task " + task.id() +
                                    " dispatch failed: Worker is\
                                      unable to do the task.")
            return False

        return True

    def _dispatchSuperTask(self, task: SuperTask) -> bool:
        ret = True
        subTasks = task.getChildren()

        for sub in subTasks:
            if not sub.isPrepare():
                continue

            self._taskTracker.track(sub)

            do_ret = self._do_dispatch(sub)

            if do_ret is False:
                ret = False
            else:
                sub.stateChange(Task.STATE_IN_PROC)

        if ret is True:
            self._dispatch_logging("SuperTask " + task.id() +
                                    " is dispatched completly")
            task.stateChange(Task.STATE_IN_PROC)
        else:
            self._dispatch_logging("SuperTask " + task.id() +
                                    " is not dispatched completly")

        return ret

    def dispatch(self, task: Task) -> bool:
        self._dispatch_logging("Dispatch task " + task.id())

        if self._taskTracker.isInTrack(task.id()):
            task_exists = self._taskTracker.getTask(task.id())

            assert(task_exists is not None)
            task_exists.refs += 1

            return True

        # Bind task with a build or buildSet
        task = self._bind(task)

        self._taskTracker.track(task)

        with self.dispatchLock:
            if self._dispatch(task) == False:
                # fixme: Queue may full while inserting
                self.taskWait.insert(0, task)
                self.taskEvent.set()

            return True

    def redispatch(self, task: Task) -> bool:
        taskId = task.id()

        self._dispatch_logging("Redispatch task " + taskId)

        if self._taskTracker.isInTrack(taskId):
            ret = task.stateChange(Task.STATE_PREPARE)
            if ret is Error:
                return False

            self._taskTracker.untrack(taskId)

        with self.dispatchLock:
            if self._do_dispatch(task) is False:
                self.taskWait.insert(0, task)
                self._taskTracker.track(task)
                self.taskEvent.set()

        return True

    def _bind(self, task:Task) -> Task:
        if not task.isBindWithBuild():
            # To check taht whether the task bind with
            # a build or BuildSet. If not bind just to
            # bind one with it.
            info = self._sInst.getModule(INFO_M_NAME) # type: Info
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

            try:
                task = task.transform()
            except:
                traceback.print_exc()

        return task


    # Dispatcher thread is response to assign task in queue which name is taskWait
    def run(self) -> None:
        counter = 0

        last_aging = datetime.utcnow()
        needAging = lambda now, last: (now - last).seconds > 1

        while True:

            # Aging
            now = datetime.utcnow()
            if needAging(now, last_aging):
                # Remove oudated tasks
                self._taskAging()

                last_aging = now

            # Is there any task in taskWait queue
            # fixme: need to setup a timeout value
            isArrived = self.taskEvent.wait(2)

            if len(self.taskWait) == 0:
                self._dispatch_logging("TaskWait Queue is empty.")
                self.taskEvent.clear()

                continue

            task = self.taskWait.pop()
            self._dispatch_logging("Task " + task.id() + " arrived")

            if task.state == Task.STATE_FAILURE:
                continue

            # Is there any workers acceptable
            workers = self._workers.getWorkerWithCond(acceptableWorkers)

            if workers == []:
                self._dispatch_logging("No acceptable worker")
                self.taskWait.append(task)
                time.sleep(1)
            else:
                # Task can be drop via setting its state to STATE_FAILURE
                self._dispatch_logging("Dispatch task: " + task.id())

                if self._dispatch(task) is False:
                    self._dispatch_logging("Dispatch task " + task.id() +
                                            " failed. append to tail of queue")
                    self.taskWait.append(task)

                    time.sleep(1)


    def _taskAging(self) -> None:
        tasks = self._taskTracker.tasks()

        current = datetime.utcnow()
        cond_is_timeout = lambda t: (current - t.last()).seconds > 5

        # For a task that refs reduce to 0 do aging instance otherwise wait 1 min
        tasks_outdated = [t for t in tasks if t.refs == 0 or cond_is_timeout(t)]

        idents_outdated = [t.id() for t in tasks_outdated]
        self._dispatch_logging("Outdate tasks:" + str(idents_outdated))

        for ident in idents_outdated:
            if not self._taskTracker.isInTrack(ident):
                continue

            t = self._taskTracker.getTask(ident)
            assert(t is not None)

            # Task in proc or prepare status
            # will not be aging even though
            # their counter is out of date.
            if t.isProc() or t.isPrepare():

                if self._workers.getNumOfWorkers() is not 0:
                    self._dispatch_logging(
                        "Task " + ident + "is in processing/Prepare. Abort to remove")
                    continue

            self._dispatch_logging("Remove task " + ident)
            self._taskTracker.untrack(ident)

    # Cancel a task
    # This method cannot cancel a member of a SuperTask
    # but this method can cancel a SuperTask.
    def cancel(self, taskId: str) -> None:
        task = self._taskTracker.getTask(taskId)

        if task is None:
            return None

        if isinstance(task, SingleTask):
            if task.isAChild():
                # This task is a member of a SuperTask
                # cancel a member of a SuperTask here
                # is not allowed.
                return None

            theWorker = self._taskTracker.whichWorker(task.id())
            if theWorker is not None:
                theWorker.cancel(task.id())

        elif isinstance(task, PostTask):
            # PostTask must a member of a SuperTask
            return None

        elif isinstance(task, SuperTask):
            children = task.getChildren()

            for child in children:
                theWorker = self._taskTracker.whichWorker(child.id())

                if theWorker is not None:
                    theWorker.cancel(child.id())

                child.stateChange(Task.STATE_FAILURE)

        task.stateChange(Task.STATE_FAILURE)

    # Cancel all tasks processing on a worker
    def cancelOnWorker(self, wId: str) -> None:
        pass

    def removeTask(self, taskId: str) -> None:
        self._taskTracker.untrack(taskId)

    def getTask(self, taskId:str) -> Optional[Task]:
        return self._taskTracker.getTask(taskId)

    def getTaskInWaits(self) -> List[Task]:
        return self.taskWait

    # Use to get result of task
    # after the call of this method task will be
    # remove from _tasks
    def retrive(self, taskId: str) -> Optional[str]:
        if not self._taskTracker.isInTrack(taskId):
            return None

        task = self._taskTracker.getTask(taskId)
        if task is None:
            return None

        if not task.isFinished():
            return None

        if task.refs > 0:
            task.refs -= 1

        return task.data

    def taskState(self, taskId: str) -> int:
        if not self._taskTracker.isInTrack(taskId):
            return Error

        task = self._taskTracker.getTask(taskId)
        if task is None:
            return Error

        return task.taskState()

    def isTaskExists(self, taskId: str) -> bool:
        return self._taskTracker.isInTrack(taskId)

    def _isTask(self, taskId: str, state: Callable) -> bool:
        if not self._taskTracker.isInTrack(taskId):
            return False

        task = self._taskTracker.getTask(taskId)
        if task is None:
            return False

        return state(task)

    def isTaskPrepare(self, taskId: str) -> bool:
        return self._isTask(taskId, lambda t: t.taskState() == Task.STATE_PREPARE)

    def isTaskInProc(self, taskId: str) -> bool:
        return self._isTask(taskId, lambda t: t.taskState() == Task.STATE_IN_PROC)

    def isTaskFailure(self, taskId: str) -> bool:
        return self._isTask(taskId, lambda t: t.taskState() == Task.STATE_FAILURE)

    def isTaskFinished(self, taskId: str) -> bool:
        return self._isTask(taskId, lambda t: t.taskState() == Task.STATE_FINISHED)

    def taskLastUpdate(self, taskId: str) -> None:
        if not self._taskTracker.isInTrack(taskId):
            return None

        task = self._taskTracker.getTask(taskId)
        if task is None:
            return None

        task.lastUpdate()

def workerLost_redispatch(dispatcher: Dispatcher, data: Tuple[int, Worker]) -> None:

    event, worker = data

    if event != 1:
        return None

    if not isinstance(worker, Worker):
        return None

    tasks = worker.inProcTasks()

    for t in tasks:
        assert(isinstance(t, SingleTask) or isinstance(t, PostTask))

        # Not to redispatch tasks that need post-processing.
        if worker.role is Role_Listener and t.isAChild():
            parent = t.getParent()
            assert(parent is not None)

            parent.toState_force(Task.STATE_FAILURE)
            continue

        elif t.isAChild():
            parent = t.getParent()
            assert(parent is not None)

            t.stateChange(Task.STATE_PREPARE)
            if parent.taskState() == Task.STATE_IN_PROC:
                parent.toPreState()
                dispatcher.redispatch(parent)
        else:
            dispatcher.redispatch(t)


    # Remove all tasks in failure state.
    if worker.role is Role_Listener:
        dispatcher.notify(None)

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
    f_online_acceptable = lambda w: w.isOnline() and \
        w.isAbleToAccept() and w.role is not None

    return list(filter(lambda w: f_online_acceptable(w), workers))

def theListener(workers: List[Worker]) -> List[Worker]:
    return list(filter(lambda w: w.role == Role_Listener, workers))
