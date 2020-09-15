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


import unittest
import asyncio
import typing
import manager.worker.TestCases.misc.procunit as misc
import manager.worker.configs as configs

from manager.basic.info import Info
from manager.basic.letter import CommandLetter, NewLetter,\
    BinaryLetter
from manager.worker.procUnit import ProcUnit, JobProcUnit,\
    PROC_UNIT_HIGHT_OVERLOAD, PROC_UNIT_IS_IN_DENY_MODE
from manager.worker.proc_common import Output, ChannelEntry


handled = False


async def handler(unit: ProcUnit, letter: CommandLetter) -> None:
    global handled

    type = letter.getType()
    if type == "H":
        handled = True


class ProcUnitMock(ProcUnit):

    def __init__(self, ident: str) -> None:
        ProcUnit.__init__(self, ident)

        self.procLogic = None  # type: typing.Any
        self.result = False
        self._stop = False
        self.channel_data = {}  # type: typing.Dict

    async def run(self) -> None:
        await self.procLogic(self)

    async def reset(self) -> None:
        return None


class ProcUnitUnitTestCases(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self) -> None:
        self.pu = ProcUnitMock("Unit")

    async def test_ProcUnit_ProcLogic(self) -> None:
        # Setup
        self.pu.procLogic = misc.procUnitMock_Logic

        # Exercise
        self.pu.start()
        letter = CommandLetter("T", {})
        await self.pu.proc(letter)

        await asyncio.sleep(0.1)

        # Verify
        self.assertTrue(self.pu.result)
        self.assertEqual(ProcUnit.STATE_STOP, self.pu.state())

    async def test_ProcUnit_Stop(self) -> None:
        # Setup
        self.pu.procLogic = misc.procUnitMock_Logic

        # Exercise
        self.pu.start()
        self.pu.stop()

        # Verify
        self.assertEqual(ProcUnit.STATE_STOP, self.pu.state())

    async def test_ProcUnit_HightOverLoad(self) -> None:
        # Setup
        self.pu.procLogic = misc.procUnitMock_BlockTheQueue

        # Exercise
        self.pu.start()
        while True:
            try:
                await self.pu.proc(
                    CommandLetter("HIGH", {}))
            except PROC_UNIT_HIGHT_OVERLOAD:

                # Verify
                self.pu._stop = True
                self.assertTrue(ProcUnit.STATE_OVERLOAD, self.pu.state())
                self.assertTrue(self.pu._normal_space.full())

                return

        self.fail("No overload exception is raised")

    async def test_ProcUnit_DenyState(self) -> None:
        # Setup
        self.pu.procLogic = misc.procUnitMock_BlockTheQueue

        # Exercise
        self.pu.start()
        while True:
            try:
                await self.pu.proc(
                    CommandLetter("DENY", {}))
            except PROC_UNIT_HIGHT_OVERLOAD:
                pass
            except PROC_UNIT_IS_IN_DENY_MODE:
                # Verify
                self.pu._stop = True
                self.assertTrue(ProcUnit.STATE_DENY, self.pu.state())
                self.assertTrue(self.pu._normal_space.full())
                self.assertTrue(self.pu._reserved_space.full())

                return

        self.fail("Not enter deny mode")

    async def test_ProcUnit_Output(self) -> None:
        # Setup
        output = Output()
        output.setQueue(asyncio.Queue(10))
        self.pu.procLogic = misc.logic_send_packet
        self.pu.setOutput(output)

        # Exercise
        output.ready()
        self.pu.start()
        await asyncio.sleep(0.1)

        # Verify
        try:
            letter = self.pu._output_space.get_nowait()  # type: ignore
            type = letter.getType()

            success = True
        except asyncio.QueueEmpty:
            success = False

        self.assertTrue(success)
        self.assertEqual("Reply", type)


class JobProcUnitTestCases(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self) -> None:

        configs.config = Info("/home/ayden/Codebase/VerManager/manager/worker/" +
                              "TestCases/misc/jobprocunit_config.yaml")

        self.sut = JobProcUnit("JobUnit")
        self.queue = asyncio.Queue(10)  # type: asyncio.Queue

        output = Output()
        output.setQueue(self.queue)
        self.sut.setOutput(output)

        self.sut.setChannel(ChannelEntry("JobProcUnit"))

    async def test_JobProcUnit_JobProc(self) -> None:
        # Setup
        self.sut.start()

        # Exercise
        job = NewLetter("Job", "123456", "v1", "",
                        {'cmds': ["echo Doing...", "echo job > job_result"],
                         'resultPath': "./job_result"})
        await self.sut._normal_space.put(job)

        # Verify

        while True:
            letter = await asyncio.wait_for(self.queue.get(), timeout=3)

            if not isinstance(letter, BinaryLetter):
                continue

            self.assertEqual(b'job\n', letter.getContent('bytes'))
            break
