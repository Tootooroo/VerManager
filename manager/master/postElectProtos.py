# postElectProtos.py

import traceback
import asyncio

from datetime import datetime
from functools import reduce
from typing import List, Tuple, Optional, Dict

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
        (ret, ident) = await self._elect_listener()
        if ret == Error:
            return Error

        # Broadcast configuration to providers
        listener = self.group.getListener()
        assert(listener is not None)

        self._ProvidersInit(listener.getAddress())

        self.isInit = True

        return Ok

    async def _ProvidersInit(self, lisAddr: str) -> None:

        if self.group is None:
            return None

        candidates = self.group.candidateIter()
        cmd_set_provider = PostConfigCmd(lisAddr, self._proto_port,
                                         PostConfigCmd.ROLE_PROVIDER)

        inWait = {}  # type: Dict[str, Worker]
        for c in candidates:
            ret = self._send_command(c, cmd_set_provider)
            if ret is None:
                continue

            inWait[c.getIdent()] = c


        needWait = lambda t: (datetime.utcnow() - t).seconds < 1
        beginTime = datetime.utcnow()

        while needWait(beginTime):
            if len(inWait) == 0:
                break

            response = await self.waitMsg(timeout=1)
            if response is None:
                continue

            if response.getState() is CmdResponseLetter.STATE_SUCCESS:
                ident = response.getIdent()
                worker = inWait[ident]

                self.group.addProvider(worker)
                self.group.removeCandidate_(worker)

                del inWait[ident]

    def _send_command(self, w: Worker, cmd: Command, timeout=None) -> State:

        try:
            w.control(cmd)
        except (BrokenPipeError, queue_Empty):
            return Error
        except Exception:
            traceback.print_exc()
            return Error

        return Ok

    async def _send_command_and_wait(self, w: Worker,
                               cmd: Command,
                               timeout=None) -> Optional[CmdResponseLetter]:

        ret = self._send_command(w, cmd, timeout=timeout)
        if ret is Error:
            return None

        response = await self.waitMsg(timeout=timeout)
        if response is None:
            return None

        return response

    async def _elect_listener(self) -> Tuple[State, str]:

        if self.group is None:
            return (Ok, "")

        if self.group.numOfCandidates() == 0:
            return (Ok, "")

        candidates = self.group.candidates()

        listener = reduce(self._random_elect, candidates)
        if listener is None:
            raise ELECT_PROTO_INIT_FAILED

        host = listener.getAddress()
        cmd_set_listener = PostConfigCmd(host, self._proto_port,
                                         PostConfigCmd.ROLE_LISTENER)
        letter = await self._send_command_and_wait(listener,
                                             cmd_set_listener,
                                             timeout=2)
        if letter is None:
            return (Error, "")

        state = letter.getState()
        if state == CmdResponseLetter.STATE_FAILED:
            return (Error, letter.getIdent())

        self.group.setListener(listener)

        return (Ok, letter.getIdent())

    async def step(self) -> State:

        assert(self.group is not None)

        listener = self.group.getListener()

        # Listener is still online.
        candidates = self.group.candidates()

        if listener is not None:
            if candidates == []:
                return Ok
            else:
                host = listener.getAddress()
                # self.msgClear()

                self._ProvidersInit(listener.getAddress())

                return Ok

        # Reinit
        self._isInit = False

        # Move all providers into candidates
        providers = self.group.getProviders()
        for provider in providers:
            provider.role = Role_Provider
            self.group.removeProvider(provider.getIdent())
            self.group.addCandidate(provider)

        self.init()

        return Ok

    async def terminate(self) -> State:
        pass

    def _random_elect(self, w1: Worker, w2: Worker) -> Worker:
        return w1
