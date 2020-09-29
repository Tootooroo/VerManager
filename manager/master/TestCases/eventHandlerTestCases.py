# MIT License
#
# Copyright (c) 2020 Tootooroo
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
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
import shutil
import manager.master.configs as cfg

from manager.master.eventHandlers import EVENT_HANDLER_TOOLS
from typing import Any
from manager.master.task import Task, SingleTask, PostTask
from manager.basic.info import Info
from manager.basic.mmanager import MManager, Module
from manager.basic.letter import Letter, BinaryLetter, LogLetter, \
    ResponseLetter
from manager.master.workerRoom import WorkerRoom
from manager.master.eventListener import EventListener, Entry
from manager.basic.storage import Storage
from manager.master.logger import M_NAME as LOGGER_M_NAME

from manager.master.eventHandlers import \
    binaryHandler, logHandler, responseHandler


class sInst:
    def getModule(self, name: Any) -> Any:
        return Info("./config_test.yaml")


class LoggerMock(Module):

    def __init__(self) -> None:
        Module.__init__(self, LOGGER_M_NAME)
        self.q = asyncio.Queue(10)  # type: asyncio.Queue

    async def begin(self) -> None:
        return

    async def cleanup(self) -> None:
        return

    async def log_put(self, id: str, msg: str) -> None:
        await self.q.put((id, msg))


class WorkerRoomStub(WorkerRoom):

    def __init__(self) -> None:
        WorkerRoom.__init__(self, "", 0, sInst())
        self.t = Task("TID", "S", "V")

    def getTaskOfWorker(self, wId, tid) -> Task:
        return self.t

    def removeTaskFromWorker(self, wId, tid) -> None:
        return None


class EventHandlerTestCases(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self) -> None:
        self.eventL = EventListener()
        self.modules = MManager()
        self.env = Entry.EntryEnv(self.eventL, {}, self.modules)

    async def test_EventHandler_BinaryHandler(self) -> None:
        # Setup
        storage = Storage("./BinStorage", None)
        self.modules.addModule(storage)

        # Exercise
        await binaryHandler(self.env, BinaryLetter("B", b"JOB", fileName="File",
                                                   parent="Ver"))
        await binaryHandler(self.env, BinaryLetter("B", b"", fileName="File",
                                                   parent="Ver"))

        # Verify
        self.assertTrue(os.path.exists("./BinStorage/Ver/File"))

        # Teardown
        shutil.rmtree("./BinStorage")

    async def test_EventHandler_LogHandler(self) -> None:
        # Setup
        logger = LoggerMock()
        self.modules.addModule(logger)

        # Exercise
        await logHandler(self.env, LogLetter("W", "LID", "Message"))
        await logHandler(self.env, LogLetter("W", "LID", "Message1"))
        await logHandler(self.env, LogLetter("W", "LID", "Message2"))

        # Verify
        self.assertEqual(("LID", "Message"), logger.q.get_nowait())
        self.assertEqual(("LID", "Message1"), logger.q.get_nowait())
        self.assertEqual(("LID", "Message2"), logger.q.get_nowait())

    async def test_EventHandler_ResponseFin_SingleTask(self) -> None:
        # Module Setup
        storage = Storage("./StorageBIN", None)
        self.modules.addModule(storage)

        wr = WorkerRoomStub()
        wr.t = SingleTask("TID", "V", "R", None)
        wr.t.stateChange(Task.STATE_IN_PROC)
        self.modules.addModule(wr)

        logger = LoggerMock()
        self.modules.addModule(logger)

        # Setup config
        cfg.config = Info("./config.yaml")

        # Setup Handlers
        EVENT_HANDLER_TOOLS.action_init(self.env)

        # Exercise
        binary = BinaryLetter("TID", b"JOB", fileName="FILE", parent="V")
        await binaryHandler(self.env, binary)
        binary = BinaryLetter("TID", b"", fileName="FILE", parent="V")
        await binaryHandler(self.env, binary)
        response = ResponseLetter("I", "TID", Letter.RESPONSE_STATE_FINISHED)
        await responseHandler(self.env, response)

        # Verify
        os.path.exists("./data/FILE")
        os.path.exists("./public/FILE")

        # TearDown
        shutil.rmtree("./StorageBIN")
        shutil.rmtree("./data")
        shutil.rmtree("./public")
