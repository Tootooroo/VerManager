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
import os
from datetime import datetime
from manager.basic.commandExecutor import CommandExecutor


async def stopCE(ce: CommandExecutor) -> None:
    await asyncio.sleep(2)
    ce.stop()



class CommandExecutorTestCases(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self) -> None:
        self.sut = CommandExecutor()

    async def test_CE_NotrmalCommand(self) -> None:
        """
        CommandExecutor Run command
        """
        self.sut.setCommand(["echo ll > /tmp/CET_TEST"])
        await self.sut.run()

        # Verify
        os.path.exists("/tmp/CET_TEST")

        # Teardown
        os.remove("/tmp/CET_TEST")

    async def test_CE_StuckedCommand(self) -> None:
        """
        CommandExecutor run a command that stucked out of limit
        """
        self.sut.setCommand(["sleep 10"])
        self.sut.setStuckedLimit(1)

        before = datetime.now()
        await self.sut.run()
        after = datetime.now()

        # Verify
        self.assertLessEqual((after - before).seconds, 2)

    async def test_CE_TerminatedCommand(self) -> None:
        """
        CommandExecutor terminate command
        """
        self.sut.setCommand(["sleep 10"])

        await asyncio.gather(
            self.sut.run(),
            stopCE(self.sut)
        )
