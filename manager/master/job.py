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

from typing import Dict, List
from manager.master.task import Task


class Job:

    def __init__(self, jobid: str, cmd_id: str, info: Dict[str, str]) -> None:
        self.jobid = jobid
        self.cmd_id = cmd_id
        self._tasks = {}  # type: Dict[str, Task]
        self._job_info = info

    def addTask(self, task: Task) -> None:
        ident = task.id()
        if ident not in self._tasks:
            self._tasks[ident] = task

    def removeTask(self, ident: str) -> None:
        if ident in self._tasks:
            del self._tasks[ident]

    def tasks(self) -> List[Task]:
        return list(self._tasks.values())

    def get_info(self, key: str) -> str:
        return self._job_info[key]
