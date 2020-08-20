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

from manager.basic.letter import CommandLetter
from manager.worker.procUnit import ProcUnit
from manager.worker.cmdProcessor import CmdProcessor

handled = False


async def handler(unit: ProcUnit, letter: CommandLetter) -> None:
    global handled

    type = letter.getType()
    if type == "H":
        handled = True


class CmdProcessorUnitTestCases(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self) -> None:
        self.unit = CmdProcessor("Unit")

    async def test_CmdProcessor_InstallCmdProc(self) -> None:
        # Exercise
        self.unit.cmd_proc_install("H", handler)

        # Verify
        self.assertTrue(True, self.unit.is_handler_exists("H"))

    async def test_CmdProcessor_HandleCmd(self) -> None:
        # Setup
        letter = CommandLetter("H", {})
        self.unit.cmd_proc_install("H", handler)

        # Exercise
        await self.unit.start()
        await self.unit.proc(letter)

        # Verify
        self.assertTrue(handled)
