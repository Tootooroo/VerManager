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

from manager.basic.letter import CommandLetter, Letter
from manager.worker.procUnit import ProcUnit


# Things that used by ProcUnitTestCases
channel_data = {}  # type: typing.Dict


async def procUnitMock_Logic(p):

    try:
        letter = await p.job_retrive(timeout=1)
    except asyncio.exceptions.TimeoutError:
        return None

    if not isinstance(letter, CommandLetter):
        return None

    type = letter.getType()

    if type == "T":
        p.result = True
    else:
        p.result = False


async def procUnitMock_BlockTheQueue(unit):

    while True:
        await asyncio.sleep(1)


async def procUnitMock_NotifyChannel(unit: ProcUnit):
    unit._notify()


async def logic_send_packet(unit: ProcUnit):
    output = unit._output_space
    if output is None:
        return

    await output.send(CommandLetter("Reply", {}), timeout=0)


class Connector:

    def __init__(self) -> None:
        self.q = asyncio.Queue(10)  # type: asyncio.Queue

    async def sendLetter(self, letter: Letter, timeout=None) -> None:
        await self.q.put(letter)
