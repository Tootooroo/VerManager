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
import manager.master.configs as cfg

from manager.basic.info import Info
from manager.master.dispatcher import Dispatcher, WaitArea, \
    WaitAreaSpec, theListener, viaOverhead
from manager.master.workerRoom import WorkerRoom
from manager.master.taskTracker import TaskTracker
from manager.master.TestCases.misc.workerStub import WorkerStub
from manager.master.worker import Worker
from manager.master.task import Task, SingleTask, SuperTask, PostTask
from manager.master.build import Build, BuildSet


class sInst:
    def getModule(self, name: typing.Any) -> typing.Any:
        return Info("./config_test.yaml")


class MsgPri0:

    def __init__(self, msg: str) -> None:
        self.msg = msg


class MsgPri1:

    def __init__(self, msg: str) -> None:
        self.msg = msg


class MsgPri2:

    def __init__(self, msg: str) -> None:
        self.msg = msg


async def msgCheck(self, t) -> None:
    for i in range(10):
        msg = await self.sut.dequeue(timeout=1)
        if not isinstance(msg, t):
            self.fail("Wrong Message type")
        self.assertEqual(str(i), msg.msg)


def msgCheck_nowait(self, t) -> None:
    for i in range(10):
        msg = self.sut.dequeue_nowait()
        if not isinstance(msg, t):
            self.fail("Wrong Message type")
        self.assertEqual(str(i), msg.msg)


class WaitAreaTestCases(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self) -> None:
        self.sut = WaitArea("Area", [
            WaitAreaSpec("MsgPri0", 0, 10),
            WaitAreaSpec("MsgPri1", 1, 10),
            WaitAreaSpec("MsgPri2", 2, 10),
        ])

    async def test_WaitArea_EnqueueDequeue(self) -> None:
        # Exercise
        for i in range(10):
            await self.sut.enqueue(MsgPri0(str(i)), timeout=1)
            await self.sut.enqueue(MsgPri1(str(i)), timeout=1)
            await self.sut.enqueue(MsgPri2(str(i)), timeout=1)

        # Verify
        await msgCheck(self, MsgPri0)
        await msgCheck(self, MsgPri1)
        await msgCheck(self, MsgPri2)

    async def test_WaitArea_EnqueueDequeue_No_Wait(self) -> None:
        # Exercise
        for i in range(10):
            self.sut.enqueue_nowait(MsgPri0(str(i)))
            self.sut.enqueue_nowait(MsgPri1(str(i)))
            self.sut.enqueue_nowait(MsgPri2(str(i)))

        # Verify
        msgCheck_nowait(self, MsgPri0)
        msgCheck_nowait(self, MsgPri1)
        msgCheck_nowait(self, MsgPri2)

    async def test_WaitArea_EnQueueWrongType(self) -> None:
        # Exercise and Verify
        try:
            await self.sut.enqueue(1)
        except WaitArea.Area_unknown_task:
            return

        self.fail("Error Type enqueue success is not allowed")

    async def test_WaitArea_Peek(self) -> None:
        # Exercise
        await self.sut.enqueue(MsgPri0("Head"))
        await self.sut.enqueue(MsgPri1("Tail"))

        # Verify
        msg = self.sut.peek()
        self.assertEqual("Head", msg.msg)

    async def test_WaitArea_PeekEmptyQueue(self) -> None:
        # Exercise and Verify
        msg = self.sut.peek()
        self.assertEqual(None, msg)


class DispatcherUnitTest(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self) -> None:
        self.wr = WorkerRoom("127.0.0.1", 30001, sInst())
        self.tt = TaskTracker()

        self.sut = Dispatcher()
        self.sut.setWorkerRoom(self.wr)
        self.sut.setTaskTracker(self.tt)

        self.sut.add_worker_search_cond(SingleTask, viaOverhead)
        self.sut.add_worker_search_cond(PostTask, theListener)

        # Add Workers
        self.n = normal_worker = WorkerStub("Normal", Worker.ROLE_NORMAL)
        normal_worker.setState(Worker.STATE_ONLINE)
        normal_worker.max = 1

        self.m = merger = WorkerStub("Merger", Worker.ROLE_MERGER)
        merger.setState(Worker.STATE_ONLINE)
        merger.max = 1

        self.wr.addWorker(normal_worker)
        self.wr.addWorker(merger)

    async def test_Dispatcher_Dispatch(self) -> None:
        """
        Dispatch a SingleTask to Workers.
        Only one of worker can receive dispatched task
        """

        # Exercise
        self.sut.dispatch(
            SingleTask("Single", "V", "R",
                       Build("B", {"cmd": "...", "output": "..."}))
        )
        await asyncio.sleep(0.1)

        # Verify

        # At least one of workers is deal with the task
        self.assertTrue(
            self.n.in_doing_task or self.m.in_doing_task
        )

        # Make sure only one worker receive the task
        self.assertTrue(
            self.n.in_doing_task is None or
            self.m.in_doing_task is None
        )

    async def test_Dispatcher_DispatchPostTask(self) -> None:
        """
        Dispatch a PostTask to workers.
        PostTask should only dispatch to Merger.
        """

        # Exercise
        self.sut.dispatch(PostTask("P", "V", [], None))
        await asyncio.sleep(0.1)

        # Verify
        # Make sure merger is doing the task and
        # normal is not.
        self.assertTrue(self.m.in_doing_task and self.n.in_doing_task is None)

    async def test_Dispatcher_Dispatch_SuperTask(self) -> None:
        """
        Dispatch a SuperTask.
        """

        # Setup
        cfg.config = Info("./config.yaml")

        # Exercise
        buildSet = BuildSet(cfg.config.getConfig("BuildSet"))
        task = Task("S", "S", "R", extra={})
        task.setBuild(buildSet)
        task = task.transform()

        self.sut.dispatch(task)
        await asyncio.sleep(0.1)

        # Verify
        self.assertEqual(self.n.postCount, 0)
        self.assertEqual(self.m.postCount, 1)
        self.assertEqual(self.n.singleCount+self.m.singleCount, 4)

    async def test_Dispatcher_DispatchSuperTask_MergerLost(self) -> None:
        """
        Merger lost while dispatch SuperTask
        """

        # Setup
        cfg.config = Info("./config.yaml")
        self.m.setState(Worker.STATE_OFFLINE)

        # Exercise
        buildSet = BuildSet(cfg.config.getConfig("BuildSet"))
        task = Task("S", "S", "R", extra={})
        task.setBuild(buildSet)
        task = task.transform()

        self.sut.dispatch(task)
        self.sut.start()
        await asyncio.sleep(3)

        # Verify
        self.assertTrue(len(self.n.cancel_jobs) == 4)
        self.assertTrue('S__GL5610' in self.n.cancel_jobs)
        self.assertTrue('S__GL5610-v3' in self.n.cancel_jobs)
        self.assertTrue('S__GL8900_line' in self.n.cancel_jobs)
        self.assertTrue('S__GL8900_ctrl' in self.n.cancel_jobs)

    async def test_Dispatcher_Aging_SingleTask(self) -> None:
        """
        Aging SingleTask
        """

        # Setup
        cfg.config = Info("./config.yaml")

        # Exercise
        build = Build("B", {"cmd": "...", "output": "..."})
        t = SingleTask("S", "V", "R", build)
        self.sut._taskTracker.track(t)  # type: ignore
        t.state = Task.STATE_FINISHED
        self.sut.start()

        # Verify
        await asyncio.sleep(5)
        self.assertFalse(
            self.sut._taskTracker.isInTrack("S")  # type: ignore
        )

    async def test_Dispatcher_Aging_SuperTask_INPROC(self) -> None:
        # Setup
        cfg.config = Info("./config.yaml")

        # Exercise
        bs = BuildSet(cfg.config.getConfig("BuildSet"))
        t = SuperTask("S", "V", "R", bs, {})

        # Set state of tasks to Fin
        t.state = Task.STATE_IN_PROC
        for task in t.getChildren():
            task.state = Task.STATE_IN_PROC
            self.sut._taskTracker.track(task)  # type: ignore

        self.sut._taskTracker.track(t)  # type: ignore
        self.sut.start()

        # Verify
        await asyncio.sleep(5)
        self.assertTrue(
            self.sut._taskTracker.isInTrack("S__GL5610")  # type: ignore
        )

    async def test_Dispatcher_Aging_SuperTask_CASE_1(self) -> None:
        """
        All SingleTask of a SuperTask is in Fin and Post is IN_PROC
        Those SingleTask should not be aging.
        """

        # Setup
        cfg.config = Info("./config.yaml")

        # Exercise
        bs = BuildSet(cfg.config.getConfig("BuildSet"))
        t = SuperTask("S", "V", "R", bs, {})
        self.sut._taskTracker.track(t)  # type: ignore

        # Set state of tasks
        t.state = Task.STATE_IN_PROC
        for task in t.getChildren():
            if isinstance(task, SingleTask):
                task.state = Task.STATE_FINISHED
            elif isinstance(task, PostTask):
                task.state = Task.STATE_IN_PROC

            self.sut._taskTracker.track(task)  # type: ignore

        self.sut.start()

        # Verify
        await asyncio.sleep(5)
        for task in t.getChildren():
            self.assertTrue(
                self.sut._taskTracker.isInTrack(task.id())  # type: ignore
            )