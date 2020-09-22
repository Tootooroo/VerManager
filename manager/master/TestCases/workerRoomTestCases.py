# WorkerRoom Testcases

import unittest
import asyncio

from manager.master.worker import Worker
from manager.basic.letter import Letter, PropLetter, receving, \
    CommandLetter, CmdResponseLetter, sending
from manager.master.workerRoom import WorkerRoom
from typing import Any, Optional, Tuple
from manager.basic.info import Info
from manager.basic.observer import Subject
from manager.basic.stubs.virtualMachine import VirtualMachine


class sInst:
    def getModule(self, name: Any) -> Any:
        return Info("./config_test.yaml")


class VirtualWorker(VirtualMachine):

    async def run(self) -> None:
        r, w = await asyncio.open_connection(self._host, self._port)

        self.r = r
        self.w = w

        propLetter = PropLetter(self._ident, "1", "0", Worker.ROLE_MERGER)
        await sending(w, propLetter)

        await asyncio.sleep(10)


class VirtualWorker_Reconnect(VirtualWorker):

    async def run(self) -> None:
        await VirtualWorker.run(self)

        # Disconnect
        self.w.close()

        # Reconnect
        await VirtualWorker.run(self)


class VirtualWorker_Lost(VirtualWorker):

    async def run(self) -> None:
        await VirtualWorker.run(self)
        # Disconnect
        self.w.close()

        self.q.put((WorkerRoom.EVENT_DISCONNECTED, self._ident))

class WorkerRoomTestCases(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self) -> None:
        self.wr = WorkerRoom("127.0.0.1", 30000, sInst())
        self.v_wr1 = VirtualWorker("w1", "127.0.0.1", 30000)
        self.v_wr2 = VirtualWorker("w2", "127.0.0.1", 30000)

    async def test_WorkerRoom_Connect(self) -> None:
        # Exercise
        self.wr.start()
        await asyncio.sleep(0.1)

        # Start Worker1 and worker2
        self.v_wr1.start()
        self.v_wr2.start()
        await asyncio.sleep(1)

        # Verify
        self.assertTrue(self.wr.isExists("w1"))
        self.assertTrue(self.wr.isExists("w2"))

    async def test_WorkerRoom_ConnectDup(self) -> None:
        # Setup
        self.v_wr2._ident = "w1"

        # Exercise
        self.wr.start()
        await asyncio.sleep(0.1)

        self.v_wr1.start()
        self.v_wr2.start()
        await asyncio.sleep(0.1)

        # Verify
        self.assertEqual(self.wr.getNumOfWorkers(), 1)

    async def test_WorkerRoom_ReconnWithinWaitInterval(self) -> None:
        # Setup
        self.v_wr1 = VirtualWorker_Reconnect("w1", "127.0.0.1", 30000)
        self.v_wr2 = VirtualWorker_Reconnect("w2", "127.0.0.1", 30000)

        # Exercise
        self.wr.start()
        await asyncio.sleep(0.1)

        self.v_wr1.start()
        self.v_wr2.start()
        await asyncio.sleep(0.1)

        # Verify
        self.assertTrue(self.wr.isExists("w1"))
        self.assertTrue(self.wr.isExists("w2"))

    def test_WorkerRoom_lisAddrUpdate(self) -> None:
        pass

    def test_WorkerRoom_LisLost(self) -> None:
        pass

    async def test_WorkerRoom_WorkerLost(self) -> None:
        # Setup
        self.v_wr1 = VirtualWorker_Lost("w1", "127.0.0.1", 30000)
        self.v_wr2 = VirtualWorker_Lost("w2", "127.0.0.1", 30000)

        # Exercise
        self.wr.start()
        await asyncio.sleep(0.1)

        self.v_wr1.start()
        self.v_wr2.start()
        await asyncio.sleep(10)

        # Verify
        self.assertFalse(self.wr.isExists("w1"))
        self.assertFalse(self.wr.isExists("w2"))
