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
    # DENY state means ProcUnit is unable
    # to accept any more jobs.
    STATE_DENY = 2

    def __init__(self, ident: str) -> None:
        self._unitIdent = ident

        self._state = self.STATE_STOP

        self._install = False

        # Queue to notify message to Processor
        # which is call by ProcUnit.
        # Will be initialized when install into Processor
        self._notify_queue = None  # type: Optional[asyncio.Queue]

        # Used by query method to generate message need by
        # caller the type of content is depend on code param
        # of query().
        self._querySources = {}  # type: Dict[int, Callable]

        # Similar to _querySources
        self._ctrlHandlers = {}  # type: Dict[int, Callable]

        self._letter_queue = asyncio.Queue(256)  # type: asyncio.Queue[Letter]
        self._letter_reserved_space = asyncio.Queue(128)  \
            # type: asyncio.Queue[Letter]

    @abc.abstractmethod
    async def run(self) -> None:
        """
        Start the ProcUnit. After started it will
        handle letter receive from Processor
        """

    @abc.abstractmethod
    async def proc(self, letter: Letter) -> None:

        try:
            self._letter_queue.put_nowait(letter)

        except asyncio.QueueFull:
            if self._store_job_to_reserved_space(letter) is True:
                raise PROC_UNIT_HIGHT_OVERLOAD(self._unitIdent)
            else:
                raise PROC_UNIT_IS_IN_DENY_MODE(self._unitIdent)

    async def _store_job_to_reserved_space(self, letter: Letter) -> bool:
        try:
            self._letter_reserved_space.put_nowait(letter)
            return True
        except asyncio.QueueFull:
            return False

    @abc.abstractmethod
    async def query(self, code: int) -> None:
        """ Interface to query information within unit """

    @abc.abstractmethod
    async def ctrl(self, code: int) -> None:
        """ Interface to contrl proc unit """

    async def _notify(self, message: str, timeout: int = None) -> None:
        if self._notify_queue is None:
            return None

        try:
            await asyncio.wait_for(
                self._notify_queue.put(message),
                timeout=timeout)
        except asyncio.exceptions.TimeoutError:
            pass


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
