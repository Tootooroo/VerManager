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
from manager.master.job import Job
from manager.master.task import Task


class JobTestCases(unittest.IsolatedAsyncioTestCase):

    async def test_Job_Create(self) -> None:
        # Setup & Exercise
        job = Job("JobId", "JobCommandId", {})

        # Verify
        self.assertIsNotNone(job)

    async def test_Job_Tasks(self) -> None:
        # Setup
        job = Job("jobId", "JobCommandId", {})

        # Exercise
        job.addTask("ID", Task("ID", "SN", "VSN"))

        # Verify
        self.assertTrue(len(job.tasks()) == 1)

    async def test_Job_toString(self) -> None:
        # Setup
        job = Job("JobId", "JobCmd", {})

        # Exercise
        job.addTask("ID1", Task("ID1", "SN", "VSN"))
        job.addTask("ID2", Task("ID2", "SN", "VSN"))

        # Verify
        self.assertEqual("JobId::ID1:ID2", str(job))
