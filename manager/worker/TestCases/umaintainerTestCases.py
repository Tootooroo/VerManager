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
import unittest
import typing
from manager.worker.processor_comps import UnitMaintainer
from manager.worker.procUnit import ProcUnit
from manager.worker.TestCases.misc.procunit import ProcUnitStub_Dirty
from manager.worker.channel import ChannelEntry


class UnitMaintainerTestCase(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self) -> None:
        self.uc = {}  # type: typing.Dict[str, ProcUnit]
        self.um = UnitMaintainer(self.uc)
        self.um._notifyQ = asyncio.Queue(10)

    async def test_UnitMaintainer_DirtyProcUnit_Dealwith(self) -> None:
        # Setup
        unit1 = self.uc["U1"] = ProcUnitStub_Dirty("U1", "JOB")
        unit1._channel = ChannelEntry("U1")

        unit1._channel.addReceiver(self.um)
        self.um.addTrack("U1", unit1._channel.info)

        # Exercise
        self.um.start()
        await asyncio.sleep(1)

        unit1.start()
        await asyncio.sleep(1)

        # Verify
        self.assertTrue(unit1._state == ProcUnit.STATE_READY)
