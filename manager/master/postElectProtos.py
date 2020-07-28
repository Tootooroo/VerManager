# postElectProtos.py

import unittest
import traceback
import asyncio
import manager.basic.letter as L

from datetime import datetime
from functools import reduce
from typing import List, Tuple, Optional, Dict, Any

from queue import Empty as queue_Empty
from manager.basic.type import Ok, Error, State
from manager.basic.letter import CmdResponseLetter
from manager.basic.commands import Command, PostConfigCmd
from manager.master.worker import Worker
from manager.master.postElection import PostElectProtocol, Role_Provider


class ELECT_PROTO_INIT_FAILED(Exception):
    pass


class RandomElectProtocol(PostElectProtocol):

    def __init__(self) -> None:
        PostElectProtocol.__init__(self)
        self._blackList = []  # type: List[str]
        self._proto_port = 8066

    async def init(self) -> State:
        # group maybe None because WorkerRoom is in instable status
        if self.group is None:
            return Error

        if self.group.numOfCandidates() == 0:
            return Error

        # Listener elect
        ret, ident = await self._elect_listener()
        if ret == Error:
            return Error

        # Broadcast configuration to providers
        listener = self.group.getListener()
        assert(listener is not None)
        await self._ProvidersInit(listener.getAddress())

        self.isInit = True

        return Ok

    async def _ProvidersInit(self, lisAddr: str) -> None:

        if self.group is None:
            return None

        candidates = self.group.candidateIter()
        cmd_set_provider = PostConfigCmd(
            lisAddr, self._proto_port, PostConfigCmd.ROLE_PROVIDER)

        inWait = {}  # type: Dict[str, Worker]
        for c in candidates:
            ret = await self._send_command(c, cmd_set_provider)
            if ret is None:
                continue
            inWait[c.getIdent()] = c

        while True:
            if len(inWait) == 0:
                break

            response = await self.waitMsg(timeout=1)
            if response is None:
                continue

            if response.getState() is CmdResponseLetter.STATE_SUCCESS:
                ident = response.getIdent()

                if ident in inWait:
                    worker = inWait[ident]
                    self.group.addProvider(worker)
                    self.group.removeCandidate_(worker)
                    del inWait[ident]
                else:
                    # Letter is response to previous init. Just
                    # ignore this response
                    continue

    async def _send_command(self, w: Worker, cmd: Command) -> State:
        try:
            await w.control(cmd)
        except (BrokenPipeError, queue_Empty):
            return Error
        except Exception:
            traceback.print_exc()
            return Error

        return Ok

    async def _send_command_and_wait(self, w: Worker,
                               cmd: Command,
                               timeout=None) -> Optional[CmdResponseLetter]:

        ret = await self._send_command(w, cmd)
        if ret is Error:
            return None

        while True:
            response = await self.waitMsg(timeout=timeout)
            if response is None:
                return None
            else:
                return response

    async def _elect_listener(self) -> Tuple[State, str]:
        candidates = self.group.candidates()  # type: ignore

        # Elect listener
        listener = reduce(self._random_elect, candidates)
        if listener is None:
            raise ELECT_PROTO_INIT_FAILED

        # Listener setup
        host = listener.getAddress()
        cmd_set_listener = PostConfigCmd(
            host, self._proto_port, PostConfigCmd.ROLE_LISTENER)

        letter = await self._send_command_and_wait(
            listener, cmd_set_listener, timeout=2)

        # Check setup result
        if letter is None:
            return (Error, "")

        if letter.getType() == L.Letter.CmdResponse:
            state = letter.getState()

            isListener = letter.getExtra('isListener')
            if isListener is None or isListener == 'false':
                return (Error, "")

            if state == CmdResponseLetter.STATE_FAILED:
                return (Error, letter.getIdent())

            self.group.setListener(listener)  # type: ignore
            return (Ok, letter.getIdent())
        else:
            return (Error, "")

    async def step(self) -> State:
        assert(self.group is not None)
        candidates = self.group.candidates()
        listener = self.group.getListener()

        # Listener is still online.
        if listener is not None:
            if candidates == []:
                return Ok
            else:
                host = listener.getAddress()
                # self.msgClear()

                await self._ProvidersInit(listener.getAddress())

                return Ok

        # Reinit
        self._isInit = False

        # Move all providers into candidates
        providers = self.group.getProviders()
        for provider in providers:
            provider.role = Role_Provider
            self.group.removeProvider(provider.getIdent())
            self.group.addCandidate(provider)

        await self.init()

        return Ok

    async def terminate(self) -> State:
        pass

    def _random_elect(self, w1: Worker, w2: Worker) -> Worker:
        return w1

# Test Cases
import unittest
from manager.master.postElection import ElectGroup
from manager.basic.stubs.workerStup import WorkerStub
from manager.basic.commands import Command

class WorkerMock(WorkerStub):

    def __init__(self, ident) -> None:
        WorkerStub.__init__(self)
        self.ident = ident

        self.asListener = False
        self.asProvider = False
        self.queue = None  # type: Optional[asyncio.Queue]

    async def control(self, cmd: Command) -> None:
        if cmd.role() == PostConfigCmd.ROLE_LISTENER:  # type: ignore
            self.asListener = True  # type: ignore
            isListener = "true"
        else:
            self.asProvider = True
            isListener = "false"

        r = CmdResponseLetter(
            self.ident, L.Letter.CmdResponse,
            CmdResponseLetter.STATE_SUCCESS, {"isListener": isListener})

        await self.reply(r)

    async def reply(self, msg: Any) -> None:
        await self.queue.put(msg)  # type: ignore


class RandomElectProtosTest(unittest.TestCase):

    def setUp(self) -> None:
        # Fixture Setup
        self.w1 = worker1 = WorkerMock("w1")
        self.w2 = worker2 = WorkerMock("w2")
        self.group = ElectGroup([worker1, worker2])

    def test_PostElectProtos_Init(self) -> None:
        async def setupCoro() -> None:
            # Fixture Setup
            self.random = RandomElectProtocol()
            self.random.setGroup(self.group)
            self.w1.queue = self.random.msgQueue
            self.w2.queue = self.random.msgQueue

            # Exercise
            ret = await self.random.init()
            self.assertEqual(0, ret)

        asyncio.run(setupCoro())

        # Verify
        self.assertTrue(self.w1.asListener)
        self.assertTrue(self.w1.asProvider)
        self.assertTrue(not self.w2.asListener)
        self.assertTrue(self.w2.asProvider)

    def test_PostElectProtos_stepListenerOnline(self) -> None:

        async def doTest() -> None:
            # Fixture Setup
            random = RandomElectProtocol()
            random.setGroup(self.group)
            self.w1.queue = random.msgQueue
            self.w2.queue = random.msgQueue

            worker3 = WorkerMock("w3")
            worker3.queue = random.msgQueue

            self.group.addCandidate(worker3)
            self.group.setListener(self.w1)

            # Exercise
            await random.step()

            # Verify
            providers = [p.ident for p in self.group.getProviders()]
            self.assertTrue("w1" in providers)
            self.assertTrue("w2" in providers)
            self.assertTrue("w3" in providers)

        asyncio.run(doTest())
