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

import asyncio
import typing

from manager.master.worker import Worker
from manager.master.task import Task, SingleTask, PostTask
from manager.basic.stubs.workerStup import \
    StreamReaderDummy, StreamWriterDummy


class WorkerStub(Worker):

    def __init__(self, ident: str, role: int) -> None:
        Worker.__init__(
            self, ident, StreamReaderDummy(), StreamWriterDummy(), role)
        self.in_doing_task = None  # type: typing.Optional[Task]
        self.postCount = 0
        self.singleCount = 0

    async def do(self, task: Task) -> None:
        self.in_doing_task = task

        if isinstance(task, SingleTask):
            self.singleCount += 1
        elif isinstance(task, PostTask):
            self.postCount += 1


class WorkerStubSendBinary(Worker):

    def __init__(self, ident: str, role: int) -> None:
        Worker.__init__(
            self, ident, StreamReaderDummy(), StreamWriterDummy(), role
        )
        self.q = asyncio.Queue(10)  # type: asyncio.Queue

    async def waitLetter(self, timeout=None) -> None:
        return await self.q.get()
