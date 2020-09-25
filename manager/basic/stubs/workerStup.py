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
from manager.master.task import Task
from manager.master.worker import Worker
from manager.basic.commands import Command


class StreamReaderDummy(asyncio.StreamReader):
    def __init__(self) -> None:
        return None


class StreamWriterDummy(asyncio.StreamWriter):
    def __init__(self) -> None:
        return None


class DO_RTN_NOT_SETED(Exception):
    pass


class CONTROL_RTN_NOT_SETED(Exception):
    pass


class WorkerStub(Worker):

    def __init__(self, ident) -> None:
        Worker.__init__(
            self,
            ident,
            StreamReaderDummy(),
            StreamWriterDummy(),
            0
        )
        self.ident = ident

    async def do(self, task: Task) -> None:
        """
        Respond to Task dispatch
        """

    async def control(self, cmd: Command) -> None:
        """
        Respond to control command
        """

    async def reply(self, msg: typing.Any) -> None:
        """
        Method to reply message to Master
        coperate with do and control method
        to work like a real Worker
        """
