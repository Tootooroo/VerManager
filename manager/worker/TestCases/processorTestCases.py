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
import manager.worker.TestCases.misc.processor as misc

from manager.worker.procUnit import ProcUnit
from manager.basic.letter import CommandLetter


class ProcessorTestCases(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self) -> None:
        self.sut = misc.ProcessorMock()

    async def test_Processor_DoCommand(self) -> None:
        # Setup
        cmdLetter1 = CommandLetter("Cmd1", {"Ident": "Cmd1"})
        cmdLetter2 = CommandLetter("Cmd2", {"Ident": "Cmd2"})

        # Exercise
        self.sut.start()
        await asyncio.sleep(0.1)

        self.sut.req(cmdLetter1)
        self.sut.req(cmdLetter2)

        self.sut.stop()

        # Verify
        self.assertTrue(self.sut.cmdDone)

    async def test_Processor_LoadProcUnit(self) -> None:
        # Setup
        unit1 = misc.ProcUnitStub("Unit1")
        unit2 = misc.ProcUnitStub("Unit2")

        self.sut.install_unit("Unit1", unit1)
        self.sut.install_unit("Unit2", unit2)

        # Exercise
        self.sut.start()
        await asyncio.sleep(0.1)

        # Verify
        self.assertEqual(ProcUnit.STATE_READY, unit1.state())
        self.assertEqual(ProcUnit.STATE_READY, unit2.state())

        self.sut.stop()

    async def test_Processor_Channel(self) -> None:
        # Setup
        unit1 = misc.ProcUnitStub("Unit1")
        unit2 = misc.ProcUnitStub("Unit2")
        component1 = misc.CompChannel()
        component2 = misc.CompChannel()

        # Exercise

        # Each of units will push 10 messages to
        # components
        self.sut.install_unit(unit1)
        self.sut.install_unit(unit2)
        self.sut.register(component1)
        self.sut.register(component2)

        self.sut.start()
        await asyncio.sleep(0.1)

        # Verify
        self.assertTrue(10, component1.msgLen("Unit1"))
        self.assertTrue(10, component2.msgLen("Unit2"))

    async def test_Processor_ChannelWithExcept(self) -> None:
        """ Pushing message should worke well after ProcUnit restart """
        # Setup
        unit1 = misc.ProcUnitStub_Except("Unit1")
        unit2 = misc.ProcUnitStub_Except("Unit2")
        component1 = misc.CompChannel()
        component2 = misc.CompChannel()

        # Exercise

        # Each of units will push 10 messages to
        # components
        self.sut.install_unit(unit1)
        self.sut.install_unit(unit2)
        self.sut.register(component1)
        self.sut.register(component2)

        self.sut.start()
        await asyncio.sleep(0.1)

        # Verify
        self.assertTrue(10, component1.msgLen("Unit1"))
        self.assertTrue(10, component2.msgLen("Unit2"))

    async def test_Processor_ProcUnitExcept(self) -> None:
        # Setup
        unit1 = misc.ProcUnitStub_Except("Unit")

        # Exercise
        # If a ProcUnit is throw an exception
        # Processor should restart this ProcUnit
        # and record it.
        self.sut.install_unit("Unit", unit1)
        self.sut.start()

        # Verify
        info = self.sut.unitInfo("Unit")

        self.assertGreater(1, info['failureCount'])
