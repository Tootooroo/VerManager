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

import abc
import asyncio
import typing

from manager.master.worker import Worker as Worker_M
from manager.basic.notify import WSCNotify
from manager.worker.connector import Connector
from manager.basic.mmanager import ModuleDaemon
from collections import namedtuple


# ident: str
# state: int
ST_MSG = namedtuple("ST_MSG", "ident state")


class CAN_NOT_FIND_MONITOR(Exception):

    def __init__(self, ident: str) -> None:
        self._ident = ident

    def __str__(self) -> str:
        return "StateObject " + self._ident + " can not find monitor."


class CAN_NOT_FIND_STATE_OBJECT(Exception):

    def __init__(self, ident: str) -> None:
        self._ident = ident

    def __str__(self) -> str:
        return "Can't find StateObject " + self._ident


class StateObject(abc.ABC):

    SO_ST_READY = 0
    SO_ST_PENDING = 1

    def __init__(self, ident: str) -> None:
        self._ident = ident
        self._state = StateObject.SO_ST_READY
        self._notifyQ = None  # type: typing.Optional[asyncio.Queue]

    def ident(self) -> str:
        return self._ident

    def setQ(self, queue: asyncio.Queue) -> None:
        self._notifyQ = queue

    async def ready(self) -> None:
        self._state = StateObject.SO_ST_READY
        await self._notify()

    async def pending(self) -> None:
        self._state = StateObject.SO_ST_PENDING
        await self._notify()

    async def _notify(self) -> None:
        if self._notifyQ is None:
            raise CAN_NOT_FIND_MONITOR(self._ident)
        await self._notifyQ.put(ST_MSG(self._ident, self._state))

    def state(self) -> int:
        return self._state

    def setState(self, state: int) -> None:
        if state == StateObject.SO_ST_PENDING or \
           state == StateObject.SO_ST_READY:

            self._state = state


class Monitor(ModuleDaemon):

    READY = 1
    PENDING = 0

    def __init__(self, workerName: str, q_size: int = 1024) -> None:
        self._workerName = workerName
        self._so = {}  # type: typing.Dict[str, StateObject]
        self._msg_q = asyncio.Queue(q_size)  # type: asyncio.Queue[ST_MSG]
        self._connector = None  # type: typing.Optional[Connector]
        self._state = Monitor.READY

    async def begin(self) -> None:
        return None

    async def cleanup(self) -> None:
        return None

    def setupConnector(self, connector: Connector) -> None:
        self._connector = connector

    def track(self, so: StateObject) -> None:
        self._so[so.ident()] = so
        so.setQ(self._msg_q)

    def state(self) -> typing.Optional[int]:
        return self._state

    def is_all_so_ready(self) -> bool:
        for so in self._so.values():
            if so.state() == StateObject.SO_ST_PENDING:
                return False

        return True

    def isInTrack(self, ident: str) -> bool:
        return ident in self._so

    def may_need_update(self, state: int) -> bool:
        return self._state != state

    async def run(self) -> None:

        assert(self._connector is not None)
        conn = typing.cast(Connector, self._connector)

        while True:

            # Wait for state change message
            st_msg = await self._msg_q.get()

            if self.may_need_update(st_msg.state):
                # Iterate over all SOs to check that
                # is worker is ready to work.
                if self.is_all_so_ready():
                    if self._state == Monitor.PENDING:
                        self._state = Monitor.READY
                        await conn.sendLetter(
                            WSCNotify("W", str(Worker_M.STATE_ONLINE))
                            .toLetter())
                else:
                    if self._state == Monitor.READY:
                        self._state = Monitor.PENDING
                        await conn.sendLetter(
                            WSCNotify("W", str(Worker_M.STATE_PENDING))
                            .toLetter())
            else:
                continue
