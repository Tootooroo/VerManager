# WorkerRoom Testcases

import unittest
import asyncio
import time

from manager.basic.letter import PropLetter, receving
from manager.master.workerRoom import WorkerRoom
from typing import Any, Optional, Tuple
from manager.basic.info import Info


class sInst:

    def getModule(self, name: Any) -> Any:
        return Info("./config_test.yaml")


class VirtualWorker:

    def __init__(self, ident: str, wr: WorkerRoom) -> None:
        self._ident = ident
        self.stream = None \
            # type: Optional[Tuple[asyncio.StreamReader, asyncio.StreamWriter]]
        self.wr = wr

    async def connect(self, host: str, port: int) -> None:
        await asyncio.sleep(1)

        r, w = await asyncio.open_connection("127.0.0.1", 30000) \
            # type: Tuple[asyncio.StreamReader, asyncio.StreamWriter]
        self.stream = (r, w)

        self.stream[1].write(
            PropLetter(self._ident, "2", "0").toBytesWithLength()
        )
        await self.stream[1].drain()

    async def recv(self) -> Optional[Letter]:
        return await receving(self.stream[0])

    async def proto_exec(self) -> None:
        letter = self.recv()
        self.assert(letter is not None)

        if letter

    async def send(self, msg: str) -> None:
        pass


class WorkerRoomTestCases(unittest.TestCase):

    def setUp(self) -> None:
        async def doSetUp():
            self.wr = WorkerRoom("127.0.0.1", 30000, sInst())
            self.v_wr1 = VirtualWorker("w1", self.wr)
            self.v_wr2 = VirtualWorker("w2", self.wr)
            self.loop = asyncio.get_running_loop()

        asyncio.run(doSetUp())

    def test_WorkerRoom_Activate(self) -> None:
        asyncio.set_event_loop(self.loop)

        # Exercise
        async def doTest():
            self.wr._lock = asyncio.Lock()

            await asyncio.gather(
                self.wr.run(),
                self.v_wr1.connect("127.0.0.1", 30000),
                self.v_wr2.connect("127.0.0.1", 30000)
            )

        asyncio.run(doTest())

        # Verify
        workers = [w.getIdent() for w in self.wr.getWorkers()]
        self.assertTrue("w1" in workers)
        self.assertTrue("w2" in workers)

        listener = self.wr.postListener()
        self.assertIsNotNone(listener)
        self.assertTrue(
            listener.getIdent() == "w1" or \
            listener.getIdent() == "w2"
        )
