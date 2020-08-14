# MIT License
#
# Copyright (c) 2020 Gcom
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

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

    def __init__(self, t: Task, w: Optional[Worker] = None) -> None:
        self._task = t
        self._worker = w  # type: Optional[Worker]

    def onWhichWorker(self) -> Optional[Worker]:
        return self._worker

    def taskStatus(self) -> TaskType:
        return self._task.taskState()

    def setWorker(self, w: Optional[Worker]) -> None:
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
        self._tasks = {}  # type: Dict[str, TrackUnit]

    def begin(self) -> None:
        return None

    def cleanup(self) -> None:
        return None

    def track(self, t: Task) -> None:
        self._tasks[t.id()] = TrackUnit(t)

    def isInTrack(self, t_name) -> bool:
        return t_name in self._tasks

    def untrack(self, t_name: str) -> None:
        if t_name not in self._tasks:
            return None
        del self._tasks[t_name]

    def getTask(self, t_name: str) -> Optional[Task]:
        if t_name not in self._tasks:
            return None
        return self._tasks[t_name].getTask()

    def onWorker(self, t_name: str, worker: Optional[Worker]) -> None:
        if t_name not in self._tasks:
            return None

        self._tasks[t_name].setWorker(worker)

    def tasksOfWorker(self, w_name: str) -> List[Task]:
        def p(unit):
            w = unit.onWhichWorker()
            if w is not None:
                return w.getIdent() == w_name
            else:
                return False

        return [unit.getTask() for unit in self._tasks.values() if p(unit)]

    def whichWorker(self, t_name: str) -> Optional[Worker]:
        if t_name not in self._tasks:
            return None
        return self._tasks[t_name].onWhichWorker()

    def status(self, t_name) -> Optional[TaskType]:
        if t_name not in self._tasks:
            return None
        return self._tasks[t_name].taskStatus()

    def tasks(self) -> List[Task]:
        return [unit.getTask() for unit in self._tasks.values()]
