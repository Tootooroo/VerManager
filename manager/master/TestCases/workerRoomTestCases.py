# WorkerRoom Testcases

import unittest
import asyncio

from manager.basic.letter import Letter, PropLetter, receving, \
    CommandLetter, CmdResponseLetter
from manager.master.workerRoom import WorkerRoom
from typing import Any, Optional, Tuple
from manager.basic.info import Info
from manager.basic.observer import Subject


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
        self.isLis = False
        self.role = ""

    async def connect(self, host: str, port: int) -> None:
        await asyncio.sleep(1)

        r, w = await asyncio.open_connection("127.0.0.1", 30000) \
            # type: Tuple[asyncio.StreamReader, asyncio.StreamWriter]
        self.stream = (r, w)

        self.stream[1].write(
            PropLetter(self._ident, "2", "0").toBytesWithLength()
        )
        await self.stream[1].drain()

    async def disconnect(self) -> None:
        if self.stream is None:
            return None
        self.stream[1].close()

        await self.wr._eventQueue.put(self._ident)

    async def recv(self, timeout=None) -> Optional[Letter]:
        if self.stream is None:
            return None
        return await receving(self.stream[0], timeout=timeout)

    async def proto_exec(self) -> None:
        await self.proto(self)

    async def send(self, l: Letter) -> None:
        assert(isinstance(l, CmdResponseLetter))
        await self.wr.msgToPostManager(l)


class EventListenerStub(Subject):
    pass


async def proto_postElect(vir: VirtualWorker) -> None:
    try:
        letter = await vir.recv(timeout=1)
    except asyncio.exceptions.TimeoutError:
        return None

    assert(letter is not None)
    if not isinstance(letter, CommandLetter):
        return None

    isListener = ""
    type = letter.getType()
    role = letter.content_("role")

    if type != "post":
        return None

    if role == "L":
        vir.isLis = True
        vir.role = "L"
        isListener = "true"
    else:
        vir.role = "P"
        isListener = "false"

    response = CmdResponseLetter(
        vir._ident, Letter.CmdResponse,
        CmdResponseLetter.STATE_SUCCESS, {"isListener": isListener}
    )
    await vir.send(response)


async def virInit(vir: VirtualWorker) -> None:
    await vir.connect("127.0.0.1", 30000)

    while True:
        await vir.proto_exec()

        if vir.role != "":
            break


async def proto_check_lisUpdate_command(vir: VirtualWorker) -> None:
    await proto_postElect(vir)


async def workerReconnAction_beforeRemoved(vir: VirtualWorker) -> None:
    await virInit(vir)

    await vir.disconnect()
    await asyncio.sleep(2)
    await vir.connect("127.0.0.1", 30000)


async def workerDisconnect(vir: VirtualWorker) -> None:
    await virInit(vir)

    if vir.isLis:
        await vir.disconnect()


class WorkerRoomTestCases(unittest.TestCase):

    def setUp(self) -> None:
        async def doSetUp():
            self.wr = WorkerRoom("127.0.0.1", 30000, sInst())
            self.v_wr1 = VirtualWorker("w1", self.wr)
            self.v_wr2 = VirtualWorker("w2", self.wr)

        asyncio.run(doSetUp())

    def test_WorkerRoom_Activate(self) -> None:
        # Setup
        coro = None  # type: Any
        self.v_wr1.proto = proto_postElect
        self.v_wr2.proto = proto_postElect

        # Exercise
        async def worker_run(w):
            await w.connect("127.0.0.1", 30000)
            while True:
                await w.proto_exec()

        async def stop():
            nonlocal coro
            await asyncio.sleep(5)
            coro.cancel()

        async def doTest():
            nonlocal coro

            self.wr._lock = asyncio.Lock()
            self.wr._pManager._eProtocol.msgQueue = asyncio.Queue(125)

            coro = asyncio.gather(
                self.wr.run(),
                worker_run(self.v_wr1),
                worker_run(self.v_wr2),
                stop()
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
        # Setup
        coro = None  # type: Any
        self.v_wr1.proto = proto_postElect
        self.v_wr2.proto = proto_postElect

        # Exercise
        async def stop():
            await asyncio.sleep(5)
            coro.cancel()

        async def doTest():
            nonlocal coro

            self.wr._lock = asyncio.Lock()
            self.wr._pManager._eProtocol.msgQueue = asyncio.Queue(128)

            coro = asyncio.gather(
                self.wr.run(),
                workerReconnAction_beforeRemoved(self.v_wr1),
                workerReconnAction_beforeRemoved(self.v_wr2),
                stop()
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

    def test_WorkerRoom_lisAddrUpdate(self) -> None:
        # Setup
        coro = None  # type: Any
        self.v_wr1.proto = proto_postElect
        self.v_wr2.proto = proto_postElect

        # Exercise
        async def stop():
            await asyncio.sleep(5)
            coro.cancel()

        async def doTest():
            nonlocal coro

            self.wr._lock = asyncio.Lock()
            self.wr._pManager._eProtocol.msgQueue = asyncio.Queue(128)

            coro = asyncio.gather(
                stop(),
                self.wr.run(),
                workerDisconnect(self.v_wr1)
            )

            try:
                await coro
            except asyncio.exceptions.CancelledError:
                pass

        asyncio.run(doTest())

        # Verify
        workers = [w.getIdent() for w in self.wr.getWorkers()]
        self.assertTrue("w1" not in workers or "w2" not in workers)

    def test_WorkerRoom_LisLost(self) -> None:
        pass

    def test_WorkerRoom_WorkerLost(self) -> None:
        pass
