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
import os

from typing import cast
from manager.master.build import Build, BuildSet
from manager.master.task import Task
from manager.master.master import ServerInst
from manager.worker.worker import Worker
from manager.master.dispatcher import M_NAME as DISPATCH_M_NAME, \
    Dispatcher


class FunctionalTestCases(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self) -> None:
        self.master = ServerInst("127.0.0.1", 30000, "./config.yaml")
        self.worker = Worker("./manager/worker/config.yaml")
        self.worker1 = Worker("./manager/worker/config1.yaml")
        self.worker2 = Worker("./manager/worker/config2.yaml")

    async def test_Functional_Startup(self) -> None:
        # Exercise
        self.master.start()

        # Verify
        await asyncio.sleep(10)

    @unittest.skip("")
    async def test_Functional_DispatchSingleTask(self) -> None:
        # setup
        self.master.start()
        await asyncio.sleep(1)
        self.worker.start_nowait()
        await asyncio.sleep(1)

        # Exercise
        task = Task("ID", "SN", "VSN")
        build = Build("Build",
                      {"cmd": ["sleep 5", "echo HELLO > result"],
                       "output": ["./result"]})
        task.setBuild(build)
        task = task.transform()
        dispatcher = cast(Dispatcher, self.master.getModule(DISPATCH_M_NAME))

        dispatcher.dispatch(task)

        # Verify
        await asyncio.sleep(10)
        self.assertTrue(os.path.exists("./data/result"))

    @unittest.skip("")
    async def test_Functional_DispatchSuperTaskWithOnlyOneWorker(self) -> None:
        # Setup
        self.master.start()

        await asyncio.sleep(1)
        self.worker.start_nowait()

        # Exercise
        task = Task("ID", "SN", "VSN")
        bs = BuildSet(
            {"Merge": {"cmd": ["cat file1 file2 > file3"], "output": ["./file3"]},
             "Builds": {
                 "build1": {"cmd": ["echo file1 > file1"], "output": ["./file1"]},
                 "build2": {"cmd": ["echo file2 > file2"], "output": ["./file2"]},
             }
            }
        )
        task.setBuild(bs)
        task = task.transform()

        dispatcher = cast(Dispatcher, self.master.getModule(DISPATCH_M_NAME))
        dispatcher.dispatch(task)

        # Verify
        await asyncio.sleep(10)
        self.assertTrue(os.path.exists("./data/file3"))
