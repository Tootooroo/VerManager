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

import copy
import asyncio
import typing

from manager.basic.letter import CommandLetter
from manager.worker.processor import Processor
from manager.worker.procUnit import ProcUnit, UNIT_TYPE_JOB_PROC
from manager.worker.channel import ChannelReceiver


# Things that used by ProcessorTestcases
class ProcessorMock(Processor):

    def __init__(self) -> None:
        Processor.__init__(self)
        self.cmd1Done = False
        self.cmd2Done = False

    async def begin(self) -> None:
        return None

    async def cleanup(self) -> None:
        return None

    # Add Cmd1 and Cmd2 command
    async def CMD_H_CMD1(self, cl: CommandLetter) -> None:
        self.cmd1Done = True

    async def CMD_H_CMD2(self, cl: CommandLetter) -> None:
        self.cmd2Done = True


class ProcUnitStub(ProcUnit):

    def __init__(self, ident: str) -> None:
        ProcUnit.__init__(self, ident, UNIT_TYPE_JOB_PROC)

    async def reset(self) -> None:
        return None

    async def run(self) -> None:
        for i in range(10):
            if self._channel is not None:
                await self._channel.push()

        while True:
            await asyncio.sleep(1)


class ProcUnitStub_Except(ProcUnit):

    def __init__(self, ident: str) -> None:
        ProcUnit.__init__(self, ident, UNIT_TYPE_JOB_PROC)

    async def reset(self) -> None:
        return None

    async def run(self) -> None:
        raise Exception


class CompChannel(ChannelReceiver):

    def __init__(self) -> None:
        ChannelReceiver.__init__(self)
        self.history = []  # type: typing.List

    async def update(self, uid: str) -> None:
        dup = copy.deepcopy(self.channel_data[uid])
        self.history.append(dup)

    def msgLen(self) -> int:
        return len(self.history)
