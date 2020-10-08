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
# LIABILITY, WHETHER IN AN ACTION OF COTNTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


import asyncio
import unittest
from concurrent.futures import ProcessPoolExecutor
from manager.master.taskTracker import TaskTracker
from manager.master.worker import Worker
from manager.master.task import Task


class TaskTrackerTestCases(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self) -> None:
        self.sut = TaskTracker()

    async def test_TaskTracker_TrackTask(self, ) -> None:
        # Exercise
        task = Task("T", "R", "V")
        self.sut.track(task)

        # Verify
        self.assertTrue(self.sut.isInTrack("T"))
        self.assertFalse(self.sut.isInTrack("N"))

    async def test_TaskTracker_Status(self) -> None:
        # Exercise
        task = Task("T", "R", "V")
        task.stateChange(Task.STATE_FAILURE)
        self.sut.track(task)

        # Verify
        self.assertEqual(Task.STATE_FAILURE, self.sut.status("T"))

    async def test_TaskTracker_OnWorker(self) -> None:
        # Exercise
        task = Task("T", "R", "V")
        worker = Worker("W", None, None, 0)  # type: ignore

        self.sut.track(task)
        self.sut.onWorker("T", worker)

        # Verify
        self.assertEqual(worker, self.sut.whichWorker("T"))
