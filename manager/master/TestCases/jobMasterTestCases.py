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
import typing
import manager.master.configs as config
from manager.basic.info import Info
from manager.master.task import Task
from manager.master.job import Job
from manager.master.jobMaster import JobMaster, task_prefix_trim
from manager.basic.endpoint import Endpoint
from manager.models import Jobs
from asgiref.sync import sync_to_async


class DispatcherFake(Endpoint):

    def __init__(self) -> None:
        Endpoint.__init__(self)
        self.tasks = []  # type: typing.List[str]

    async def handle(self, msg: typing.Tuple[str, Task]) -> None:
        cmd, task = msg
        self.tasks.append(task.id())


class JobMasterTestCases(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self) -> None:
        # Setup
        config.config = Info("./WorkSpace/config.yaml")
        self.sut = JobMaster()

    async def test_JobMaster_Create(self) -> None:
        # Verify
        self.assertIsNotNone(self.sut)

    async def test_JobMaster_BindJob(self) -> None:
        """
        Bind a job with a Job command that defined
        in configuration file, after binded job
        will contain a set of tasks that able to
        dispatched via dispatcher.
        """
        # Setup
        job = Job("JobMasterTest1", "GL8900", {"sn": "123456", "vsn": "123456"})

        # Exercise
        self.sut.bind(job)

        # Verify
        idents = [t.id() for t in job.tasks()]
        self.assertTrue(len(job.tasks()) == 5)
        self.assertTrue("JobMasterTest1_GL5610" in idents)
        self.assertTrue("JobMasterTest1_GL5610-v3" in idents)
        self.assertTrue("JobMasterTest1_GL8900_line" in idents)
        self.assertTrue("JobMasterTest1_GL8900_ctrl" in idents)
        self.assertTrue("JobMasterTest1" in idents)

        # Teardown
        job = await sync_to_async(Jobs.objects.filter)(jobid="JobMasterTest1")
        await sync_to_async(job.delete)()  # type: ignore

    async def test_JobMaster_DoJob(self) -> None:
        """
        Assign a job to JobMaster, JobMaster should bind
        the Job with a command then dispatch tasks to
        worker via dispatcher.
        """

        # Setup
        job = Job("JobMasterTest", "GL8900", {"sn": "123456", "vsn": "123456"})
        fake = DispatcherFake()
        self.sut.set_peer(fake)

        # Exercise
        await self.sut.do_job(job)

        # Verify
        self.assertTrue(len(job.tasks()) == 5)
        self.assertTrue("JobMasterTest_GL5610" in fake.tasks)
        self.assertTrue("JobMasterTest_GL5610-v3" in fake.tasks)
        self.assertTrue("JobMasterTest_GL8900_line" in fake.tasks)
        self.assertTrue("JobMasterTest_GL8900_ctrl" in fake.tasks)
        self.assertTrue("JobMasterTest" in fake.tasks)

        # Teardown
        job = await sync_to_async(Jobs.objects.filter)(jobid="JobMasterTest")
        await sync_to_async(job.delete)()  # type: ignore


class JobMasterMiscTestCases(unittest.IsolatedAsyncioTestCase):

    async def test_JobMasterMisc_TaskPrefixTrim_ValidString(self) -> None:
        ident = "Ver_TASKID"
        self.assertEqual("TASKID", task_prefix_trim(ident))

    async def test_JobMasterMisc_TaskprefixTrim_InvalidString(self, ) -> None:
        self.assertEqual(None, task_prefix_trim(""))
        self.assertEqual(None, task_prefix_trim("1_"))
        self.assertEqual(None, task_prefix_trim("_"))
