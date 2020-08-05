# WorkerRoom Testcases

import unittest
import asyncio

from manager.basic.letter import Letter, PropLetter, receving, \
    CommandLetter, CmdResponseLetter
from manager.master.workerRoom import WorkerRoom
from typing import Any, Optional, Tuple
from manager.basic.info import Info

async def stop(coro, delay):
    await asyncio.sleep(delay)
    coro.cancel()


class sInst:

    def getModule(self, name: Any) -> Any:
        return Info("./config_test.yaml")


class VirtualWorker:

    def __init__(self, ident: str, wr: WorkerRoom) -> None:
        self._ident = ident
        self.stream = None \
            # type: Optional[Tuple[asyncio.StreamReader, asyncio.StreamWriter]]
        self.wr = wr
        self.proto = None  # type: Any

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
        if self.stream is None:
            return None
        return await receving(self.stream[0])

    async def proto_exec(self) -> None:
        self.proto(self)

    async def send(self, l: Letter) -> None:
        assert(isinstance(l, CmdResponseLetter))
        await self.wr.msgToPostManager(l)


async def proto_postElect(vir: VirtualWorker) -> None:
    letter = await vir.recv()

    assert(letter is not None)
    if not isinstance(letter, CommandLetter):
        return None

    isListener = ""
    type = letter.getType()
    role = letter.content_("role")

    if type != "post":
        return None

    if role == "L":
        isListener = "true"
    else:
        isListener = "false"

    response = CmdResponseLetter(
        vir._ident, Letter.CmdResponse,
        CmdResponseLetter.STATE_SUCCESS, {"isListener": isListener}
    )
    await vir.send(response)


class WorkerRoomTestCases(unittest.TestCase):

    def setUp(self) -> None:
        async def doSetUp():
            self.wr = WorkerRoom("127.0.0.1", 30000, sInst())
            self.v_wr1 = VirtualWorker("w1", self.wr)
            self.v_wr2 = VirtualWorker("w2", self.wr)
            self.loop = asyncio.get_running_loop()

        asyncio.run(doSetUp())

    def test_WorkerRoom_Activate(self) -> None:
        # Setup
        coro = None  # type: Any
        asyncio.set_event_loop(self.loop)
        self.v_wr1.proto = proto_postElect
        self.v_wr2.proto = proto_postElect

        # Exercise
        async def worker_run(w):
            await w.connect("127.0.0.1", 30000)
            while True:
                await w.proto_exec()

        async def doTest():
            nonlocal coro

            self.wr._lock = asyncio.Lock()
            self.wr._pManager._eProtocol.msgQueue = asyncio.Queue(125)

            coro = asyncio.gather(
                self.wr.run(),
                worker_run(self.v_wr1),
                worker_run(self.v_wr2),
                stop(coro, 4)
            )

            try:
                await coro
            except asyncio.exceptions.CancelledError:
                pass

        asyncio.run(doTest())

        # Verify
        workers = [w.getIdent() for w in self.wr.getWorkers()]
        self.assertTrue("w1" in workers)
        self.assertTrue("w2" in workers)

        listener = self.wr.postListener()
        self.assertIsNotNone(listener)
        self.assertTrue(
            listener.getIdent() == "w1" or
            listener.getIdent() == "w2"
        )

    def test_WorkerRoom_Reconnect(self) -> None:
        pass

    def test_WorkerRoom_lisAddrUpdate(self) -> None:
        pass

    def test_WorkerRoom_LisLost(self) -> None:
        pass

    def test_WorkerRoom_WorkerLost(self) -> None:
        pass
