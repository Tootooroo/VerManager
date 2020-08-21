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

from typing import Optional, Dict, Callable
from manager.basic.letter import Letter


class ProcUnit(abc.ABC):

    PROC_UNIT_STATE = int
    # A ProcUnit is in stop state before it's
    # install into Processor
    STATE_STOP = 0
    # Ready to handle letter
    STATE_READY = 1
    # Normal space is out of space
    STATE_OVERLOAD = 2
    # DENY state means ProcUnit is unable
    # to accept any more jobs.
    STATE_DENY = 3

    def __init__(self, ident: str) -> None:
        self._unitIdent = ident

        self._state = self.STATE_STOP

        self._install = False

        self._normal_space = asyncio.Queue(256)  # type: asyncio.Queue[Letter]
        self._reserved_space = asyncio.Queue(128)  \
            # type: asyncio.Queue[Letter]

    def start(self) -> None:
        # Setup state
        self._state = self.STATE_READY

        # Run ProcLogic in current loop
        asyncio.get_running_loop().\
            create_task(self.run())

        # Reset ProcUnit's state to STATE_STOP
        self._state = self.STATE_STOP

    @abc.abstractmethod
    async def run(self) -> None:
        """
        Start the ProcUnit. After started it will
        handle letter receive from Processor
        """

    async def proc(self, letter: Letter) -> None:

        try:
            self._normal_space.put_nowait(letter)

        except asyncio.QueueFull:
            await self._store_job_to_reserved_space(letter)
            raise PROC_UNIT_HIGHT_OVERLOAD(self._unitIdent)

    async def job_retrive(self, timeout=None) -> Letter:

        # Flush letters from reserved space
        # to normal space if there is any
        # letters within reserved space
        self._flush()

        return await asyncio.wait_for(
            self._normal_space.get(), timeout=timeout)

    def _flush(self) -> None:
        reserved_empty = self._reserved_space.empty()
        noSpace = self._normal_space.full()

        if reserved_empty or noSpace:
            return None

        while True:

            try:
                self._normal_space.put_nowait(
                    self._reserved_space.get_nowait())
            except (asyncio.QueueEmpty, asyncio.QueueFull):
                return None

    async def _store_job_to_reserved_space(self, letter: Letter) -> None:
        try:
            self._reserved_space.put_nowait(letter)
        except asyncio.QueueFull:
            raise PROC_UNIT_IS_IN_DENY_MODE(self._unitIdent)

    async def _notify(self, message: Dict) -> None:
        """ Notify informations of ProcUnit to Processor """

    def state(self) -> int:
        return self._state

class PROC_UNIT_HIGHT_OVERLOAD(Exception):

    def __init__(self, unit_ident: str) -> None:
        self.unit_ident = unit_ident

    def __str__(self) -> str:
        return 'ProcUnit ' + self.unit_ident + ' is overload'


class PROC_UNIT_IS_IN_DENY_MODE(Exception):

    def __init__(self, unit_ident: str) -> None:
        self.unit_ident = unit_ident

    def __str__(self) -> str:
        return 'ProcUnit ' + self.unit_ident + ' is deny jobs'
