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
import manager.worker.configs as cfg
from manager.basic.info import Info
from manager.basic.letter import Letter
from manager.worker.monitor import StateObject, Monitor
from manager.worker.connector import Connector


class ConnectorFake(Connector):

    async def sendLetter(self, letter: Letter, timeout=None) -> None:
        return None


class MonitorTestCase(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self) -> None:
        self.m = Monitor("Worker")
        cfg.config = Info("./manager/worker/config.yaml")

    async def test_Monitor_track(self) -> None:
        # Setup
        so1 = StateObject("SO1")
        so2 = StateObject("SO2")

        # Exercise
        self.m.track(so1)
        self.m.track(so2)

        # Verify
        self.assertTrue(self.m.isInTrack("SO1"))
        self.assertTrue(self.m.isInTrack("SO2"))

    async def test_Monitor_PENDING(self) -> None:
        # Setup
        self.m.setupConnector(ConnectorFake())
        so1 = StateObject("SO1")
        so2 = StateObject("SO2")

        self.m.track(so1)
        self.m.track(so2)

        self.m.start()

        # To Pending state.
        await asyncio.sleep(1)
        await so1.pending()
        self.assertTrue(self.m.state() == Monitor.READY)

        # To Ready state
        await so2.ready()
        await asyncio.sleep(1)
        self.assertTrue(self.m.state() == Monitor.PENDING)
