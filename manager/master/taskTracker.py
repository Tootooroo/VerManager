# taskTracker.py

from typing import Optional, Dict, List

from manager.master.task import Task, TaskType
from manager.master.worker import Worker
from manager.basic.mmanager import Module

M_NAME = "TrackUnit"

class TrackUnit:
    """
    TrackUnit is a box to hold reference to Object of Task and
    Object of Worker which is processing the task.

    TrackUnit should provide a expressive interface to enable
    information query from these objects.

    """

    def __init__(self, t:Task, w:Optional[Worker] = None) -> None:
        self._task = t
        self._worker = w # type: Optional[Worker]

    def onWhichWorker(self) -> Optional[Worker]:
        if self._worker is None:
            return None
        return self._worker

    def taskStatus(self) -> TaskType:
        return self._task.taskState()

    def setWorker(self, w:Worker) -> None:
        self._worker = w

    def getTask(self) -> Task:
        return self._task


class TaskTracker(Module):
    """
    TaskTracker is a database that store informations about tasks
    that live in Dispatcher. These informations should contain
    Tasks's status and which worker is the task working on.

    Caution: TrackUnit's purpose is provide an easy way to query
            informations about task and relations between task
            and another objects. You should not to edit task via
            TrackUnit.
    """

    def __init__(self) -> None:
        global M_NAME

        Module.__init__(self, M_NAME)
        self._tasks = {} # type: Dict[str, TrackUnit]

    def track(self, t:Task) -> None:
        self._tasks[t.id()] = TrackUnit(t)

    def isInTrack(self, t_name) -> bool:
        return t_name in self._tasks

    def untrack(self, t_name:str) -> None:
        if t_name not in self._tasks:
            return None
        del self._tasks [t_name]

    def getTask(self, t_name:str) -> Optional[Task]:
        if t_name not in self._tasks:
            return None
        return self._tasks[t_name].getTask()

    def onWorker(self, t_name:str, worker:Worker) -> None:
        self._tasks[t_name].setWorker(worker)

    def whichWorker(self, t_name:str) -> Optional[Worker]:
        if t_name not in self._tasks:
            return None
        return self._tasks[t_name].onWhichWorker()

    def status(self, t_name) -> Optional[TaskType]:
        if t_name not in self._tasks:
            return None
        return self._tasks[t_name].taskStatus()

    def tasks(self) -> List[Task]:
        return [unit.getTask() for unit in self._tasks.values()]
