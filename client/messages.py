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

import json
import abc
from typing import Dict, Any, List, Tuple, Generator
from manager.master.job import Job
from manager.master.task import Task


class Message(abc.ABC):

    FORMAT_TEMPLATE = '{"type": "%s", "content": %s}'

    def __init__(self, type: str, content: Dict[str, Any]) -> None:
        self.type = type
        self.content = content

    def __str__(self) -> str:
        content = str(self.content).replace("'", "\"")
        return Message.FORMAT_TEMPLATE % (self.type, content)

    def __iter__(self) -> Generator:
        yield "type", self.type
        yield "content", self.content

    @staticmethod
    def fromString(msg_str: str) -> 'Message':
        """
        Rebuild Message from string.
        """
        json_str = json.loads(msg_str)
        return Message(json_str["type"], json_str["content"])


class JobBatchMessage(Message):

    def __init__(self, msgs: List[Message]) -> None:
        Message.__init__(self, "job.msg", {
            "subtype": "batch",
            "message": [dict(msg) for msg in msgs
                        # Ensure a batch not to embed into another
                        # batch.
                        if type(msg).__name__ != "JobBatchMessage"]
        })


class JobHistoryMessage(Message):

    pass


class JobInfoMessage(Message):

    def __init__(self, jobid: str, tasks: List[List[str]]) -> None:
        Message.__init__(self, "job.msg", {
            "subtype": "info",
            "message": {"jobid": jobid, "tasks": tasks}
        })

    def jobid(self) -> str:
        return self.content["jobid"]

    def tasks(self) -> List[Tuple[str, str]]:
        return self.content["tasks"]


class JobStateChangeMessage(Message):

    def __init__(self, jobid: str, taskid: str, state: str) -> None:
        Message.__init__(self, "job.msg", {
            "subtype": "change",
            "message": {"jobid": jobid, "taskid": taskid, "state": state}
        })


class JobFinMessage(Message):

    def __init__(self, jobid: str) -> None:
        Message.__init__(self, "job.msg", {
            "subtype": "fin",
            "message": {"jobs": [jobid]}
        })


class JobFailMessage(Message):

    def __init__(self, jobid: str) -> None:
        Message.__init__(self, "job.msg", {
            "subtype": "fail",
            "message": {"jobs": [jobid]}
        })
