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
from manager.master.job import Job
from manager.master.jobMaster import JobMaster
from manager.master.master import ServerInst
from manager.worker.worker import Worker
from manager.master.dispatcher import M_NAME as DISPATCH_M_NAME, \
    Dispatcher


class FunctionalTestCases(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self) -> None:
        self.master = ServerInst("127.0.0.1", 30001, "./config_test.yaml")
        self.worker = Worker("./manager/worker/config.yaml")
        self.worker1 = Worker("./manager/worker/config1.yaml")
        self.worker2 = Worker("./manager/worker/config2.yaml")

    @unittest.skip("")
    async def test_Functional_Startup(self) -> None:
        # Exercise
        self.master.start()

        # Verify
        await asyncio.sleep(10)

    async def test_Functional_DoJob(self) -> None:
        # Setup
        self.master.start()
        await asyncio.sleep(3)
        self.worker.start_nowait()
        await asyncio.sleep(1)

        # Exercise
        job = Job("Job", "GL8900", {"sn": "123456", "vsn": "123456"})
        job_master = cast(JobMaster, self.master.getModule("JobMaster"))

        await job_master.do_job(job)

        await asyncio.sleep(3600)
