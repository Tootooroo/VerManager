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

from typing import Dict, List, Optional, Any
from manager.master.task import Task


class Job:

    STATE_PENDING = 0
    STATE_IN_PROCESSING = 1
    STATE_DONE = 2

    def __init__(self, jobid: str, cmd_id: str, info: Dict[str, str]) -> None:
        self.jobid = jobid
        self.cmd_id = cmd_id
        self._tasks = {}  # type: Dict[str, Task]
        self._job_info = info
        self.job_result = None  # type: Optional[str]
        self.state = Job.STATE_PENDING
        self.result = None  # type: Any

    def addTask(self, ident: str, task: Task) -> None:
        if ident not in self._tasks:
            self._tasks[ident] = task

    def getTask(self, taskid: str) -> Task:
        return self._tasks[taskid]

    def numOfTasks(self) -> int:
        return len(self._tasks)

    def removeTask(self, ident: str) -> None:
        if ident in self._tasks:
            del self._tasks[ident]

    def tasks(self) -> List[Task]:
        return list(self._tasks.values())

    def get_info(self, key: str) -> Optional[str]:
        if key not in self._job_info:
            return None
        return self._job_info[key]

    def is_fin(self) -> bool:
        for task in self._tasks.values():
            if not task.isFinished():
                return False

        return True

    def __str__(self) -> str:
        tasks_str = ":".join(self._tasks.keys())
        return self.jobid + "::" + tasks_str
