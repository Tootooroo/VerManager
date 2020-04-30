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
from manager.master.task import TaskState, Task, SuperTask, SingleTask, \
    PostTask, TaskType, TASK_FORMAT_ERROR
from manager.basic.type import *
from manager.master.taskTracker import TaskTracker, M_NAME as TRACKER_M_NAME
from manager.master.workerRoom import WorkerRoom
from manager.basic.commands import ReWorkCommand

class Dispatcher(ModuleDaemon, Subject, Observer):

    NOTIFY_LOG = "log"

    def __init__(self, workerRoom:WorkerRoom, inst:Any) -> None:
        global M_NAME

        ModuleDaemon.__init__(self, M_NAME)

        Subject.__init__(self, M_NAME)
        self.addType(self.NOTIFY_LOG)

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

    def begin(self) -> None:
        return None

    def cleanup(self) -> None:
        return None

    def _dispatch_logging(self, msg:str) -> None:
        self.notify(Dispatcher.NOTIFY_LOG, ("dispatcher", msg))

    # Dispatch a task to a worker of
    # all by overhead of workers
    #
    # return True if task is assign successful otherwise return False
    def _dispatch(self, task: Task) -> bool:
        ret = False

        if isinstance(task, SuperTask):
            self._dispatch_logging("Task " + task.id() + " is a SuperTask.")
            return self._dispatchSuperTask(task)

        ret = self._do_dispatch(task)
        return ret

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
            worker.do(task)
            self._taskTracker.onWorker(task.id(), worker)
        except:
            self._dispatch_logging("Task " + task.id() +
                                    " dispatch failed: Worker is\
                                      unable to do the task.")
            return False

        return True

    def _dispatchSuperTask(self, task: SuperTask) -> bool:
        subTasks = task.getChildren()

        for sub in subTasks:
            self._taskTracker.track(sub)

            ret = self._do_dispatch(sub)

            if ret is False:
                self.taskWait.insert(0, sub)
                self.taskEvent.set()

            else:
                sub.toProcState()

        task.stateChange(Task.STATE_IN_PROC)

        return True

    def dispatch(self, task: Task) -> bool:

        self._dispatch_logging("Dispatch task " + task.id())

        if self._taskTracker.isInTrack(task.id()):
            task_exists = self._taskTracker.getTask(task.id())

            assert(task_exists is not None)
            task_exists.refs += 1

            return True

        # Bind task with a build or buildSet
        try:
            task = self._bind(task)
        except TASK_FORMAT_ERROR:
            return False

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

        # Set task's state to prepare and remove worker
        # deal with it before from record.
        ret = task.stateChange(Task.STATE_PREPARE)
        self._taskTracker.onWorker(task.id(), None)

        if ret is Error:
            self._taskTracker.untrack(task.id())
            return False

        with self.dispatchLock:
            if self._do_dispatch(task) is False:
                self.taskWait.insert(0, task)
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
            except TASK_FORMAT_ERROR:
                raise TASK_FORMAT_ERROR
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

            self._dispatch_logging("InQueue:" + str([t.id() for t in self.taskWait]))

            if len(self.taskWait) == 0:
                self._dispatch_logging("TaskWait Queue is empty.")
                self.taskEvent.clear()

                continue

            task = self.taskWait.pop()

            if not self._taskTracker.isInTrack(task.id()):
                self._dispatch_logging("Task " + task.id() + " is out of date")
                continue

            self._dispatch_logging("Task " + task.id() + " arrived")

            if task.state == Task.STATE_FAILURE:
                continue

            # Is there any workers acceptable
            if isinstance(task, PostTask):
                cond = theListener
            else:
                cond = acceptableWorkers

            workers = self._workers.getWorkerWithCond(cond)

            if workers == []:
                self._dispatch_logging("No acceptable worker")
                self.taskWait.insert(0, task)
                time.sleep(1)
            else:
                # Task can be drop via setting its state to STATE_FAILURE
                self._dispatch_logging("Dispatch task: " + task.id())

                with self.dispatchLock:
                    if self._dispatch(task) is False:
                        self._dispatch_logging("Dispatch task " + task.id() +
                                                " failed. append to tail of queue")
                        self.taskWait.insert(0, task)

                        time.sleep(1)


    def _taskAging(self) -> None:
        tasks = self._taskTracker.tasks()

        current = datetime.utcnow()
        cond_is_timeout = lambda t: (current - t.last()).seconds > 10

        # For a task that refs reduce to 0 do aging instance otherwise wait 1 min
        tasks_outdated = [t for t in tasks if t.refs == 0 or cond_is_timeout(t)]

        idents_outdated = [t.id() for t in tasks_outdated]
        self._dispatch_logging("Outdate tasks:" + str(idents_outdated))

        for ident in idents_outdated:
            if not self._taskTracker.isInTrack(ident):
                continue

            t = self._taskTracker.getTask(ident)
            assert(t is not None)

            if self._workers.getNumOfWorkers() != 0:

                # Task in proc or prepare status
                # will not be aging even though
                # their counter is out of date.
                if t.isProc() or t.isPrepare():
                    self._dispatch_logging(
                        "Task " + ident + " is in processing/Prepare. Abort to remove")
                    continue
                else:
                    # Need to check that is this task dependen on another task
                    deps = t.dependedBy()

                    for dep in deps:

                        isPrepare = dep.taskState() == Task.STATE_PREPARE
                        isInProc  = dep.taskState == Task.STATE_IN_PROC

                        if isPrepare or isInProc:
                            self._dispatch_logging(
                                "Task " + ident + " is remain cause it depend on another tasks"
                            )
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

        if isinstance(task, SuperTask):
            children = task.getChildren()

            for child in children:
                child.lastUpdate()

    def workerLost_redispatch(self, worker:Worker) -> None:

        tasks = worker.inProcTasks()

        for t in tasks:
            # Clean record in TaskTracker
            # so status of TaskTracker is up to date
            # and will able to perform action depend on it.
            self._taskTracker.onWorker(t.id(), None)

        for t in tasks:

            deps = t.dependence()

            if deps == []:
                # This task is not depend on another task
                # just redispatch this task again.
                self.redispatch(t)
            else:
                """
                This task is depend on another tasks
                need to restart it by following steps:

                First: Redispatch task
                """
                self.redispatch(t)

                """
                Second: Redispatch tasks that is
                        already done by listener
                """
                tasksOnLost = self._taskTracker.tasksOfWorker(worker.getIdent())

                # Find tasks that is done and depended by this task.
                doneTasks = [task for task in tasksOnLost
                             if task.isFinished() and t in task.dependedBy()]

                for task in doneTasks:
                    self.redispatch(task)

                """
                Third: Send RE_WORK command to workers that dealing
                       dependence of this task.
                """
                pairs = [(self._taskTracker.whichWorker(dep.id()), dep.id()) for dep in deps]

                workers = {w.getIdent():w for w, t_id in pairs if w is not None}

                d = {} # type: Dict[str, List[str]]

                for p in pairs:
                    if p[0] is None: continue

                    w_id = p[0].getIdent()

                    if w_id not in d:
                        d[w_id] = []

                    d[w_id].append(p[1])

                for w in d:
                    assert(w in workers)

                    c = ReWorkCommand(d[w])

                    try:
                        workers[w].control(c)
                    except BrokenPipeError:
                        continue


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
