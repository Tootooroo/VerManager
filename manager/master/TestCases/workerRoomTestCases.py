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
from manager.basic.observer import Observer


class sInst:
    def getModule(self, name: Any) -> Any:
        return Info("./config_test.yaml")


class VirtualWorker(VirtualMachine):

    async def run(self) -> None:
        r, w = await asyncio.open_connection(self._host, self._port)

        self.r = r
        self.w = w

        propLetter = PropLetter(self._ident, "1", "0", "Merger")
        await sending(w, propLetter)


class WaitMessgComp(Observer):

    def __init__(self) -> None:
        Observer.__init__(self)
        self.conn_msg_count = 0
        self.wait_msg_count = 0
        self.remove_msg_count = 0

    async def msg_cb(self, worker: Worker) -> None:
        if worker.isOnline():
            self.conn_msg_count += 1
        elif worker.isWaiting():
            self.wait_msg_count += 1
        elif worker.isOffline():
            self.remove_msg_count += 1


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
        await self.q.put((WorkerRoom.EVENT_DISCONNECTED, self._ident))

    def setq(self, q) -> None:
        self.q = q


class WorkerRoomTestCases(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self) -> None:
        self.wr = WorkerRoom("127.0.0.1", 30001, sInst())
        self.v_wr1 = VirtualWorker("w1", "127.0.0.1", 30001)
        self.v_wr2 = VirtualWorker("w2", "127.0.0.1", 30001)

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
        self.v_wr1 = VirtualWorker_Reconnect("w1", "127.0.0.1", 30001)
        self.v_wr2 = VirtualWorker_Reconnect("w2", "127.0.0.1", 30001)

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
        self.v_wr1 = VirtualWorker_Lost("w1", "127.0.0.1", 30001)
        self.v_wr1.setq(self.wr._eventQueue)
        self.v_wr2 = VirtualWorker_Lost("w2", "127.0.0.1", 30001)
        self.v_wr2.setq(self.wr._eventQueue)

        comp = WaitMessgComp()
        comp.handler_install("WorkerRoom", comp.msg_cb)
        self.wr.subscribe(WorkerRoom.NOTIFY_CONN, comp)
        self.wr.subscribe(WorkerRoom.NOTIFY_DISCONN, comp)
        self.wr.subscribe(WorkerRoom.NOTIFY_IN_WAIT, comp)

        # Exercise
        self.wr.start()
        await asyncio.sleep(0.1)

        self.v_wr1.start()
        self.v_wr2.start()
        await asyncio.sleep(10)

        # Verify
        self.assertFalse(self.wr.isExists("w1"))
        self.assertFalse(self.wr.isExists("w2"))
        self.assertEqual(comp.conn_msg_count, 2)
        self.assertEqual(comp.wait_msg_count, 2)
        self.assertEqual(comp.remove_msg_count, 2)
