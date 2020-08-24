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

from manager.basic.letter import CommandLetter
from manager.worker.procUnit import ProcUnit, \
    PROC_UNIT_HIGHT_OVERLOAD, PROC_UNIT_IS_IN_DENY_MODE



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
        self.stop = False
        self.channel_data = {}  # type: typing.Dict

    async def run(self) -> None:
        await self.procLogic(self)


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
                self.pu.stop = True
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
                self.pu.stop = True
                self.assertTrue(ProcUnit.STATE_DENY, self.pu.state())
                self.assertTrue(self.pu._normal_space.full())
                self.assertTrue(self.pu._reserved_space.full())

                return

        self.fail("Not enter deny mode")

    async def test_ProcUnit_Channel(self) -> None:
        # Setup
        self.pu.procLogic = misc.procUnitMock_NotifyChannel

        # Exercise
        self.pu.start()
        await asyncio.sleep(0.1)

        # Verify
        self.assertTrue(len(self.pu._info) == 3)
        self.assertTrue(self.pu._info['ident'] == "Unit")
        self.assertLess(self.pu._info['uptime'], 60)
        self.assertEqual(ProcUnit.STATE_STOP, self.pu._info['state'])
