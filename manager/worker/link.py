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

import asyncio
import traceback
import typing as T
from datetime import datetime
from manager.basic.observer import Subject
from manager.basic.letter import Letter, sending, \
    HeartbeatLetter, receving


class Link:

    # state
    CONNECTED = 0
    RECONNECTING = 1
    DISCONNECTED = 2
    REMOVED = 3

    def __init__(self, ident: str, host: str, port: int,
                 reader: asyncio.StreamReader,
                 writer: asyncio.StreamWriter) -> None:
        self.ident = ident
        self.reader = reader
        self.writer = writer
        self.state = Link.CONNECTED
        self.host = host
        self.port = port


class HBLink(Link, Subject):

    # Role
    PASSIVE = 0
    ACTIVE = 1

    # state
    CONNECTED = 0
    RECONNECTING = 1
    DISCONNECTED = 2
    REMOVED = 3

    def __init__(self, ident: str, host: str, port: int,
                 reader: asyncio.StreamReader,
                 writer: asyncio.StreamWriter,
                 infos: T.Dict[str, str],
                 isActiveSide: bool = False) -> None:

        # Init as a Link
        Link.__init__(self, ident, host, port, reader, writer)

        # Init as a Subject
        Subject.__init__(self, ident)
        self.addType("LinkLost")

        self.hbCount = 0
        self.last = datetime.utcnow()
        self._infos = infos
        self._isActive = isActiveSide
        self._lock = asyncio.Lock()
        self._loop = asyncio.get_running_loop()
        self._dispatch_proc = None  \
            # type: T.Optional[T.Callable[[Letter], T.Coroutine]]

    def _hb_timeer_udpate(self) -> None:
        self.last = datetime.utcnow()

    def _hb_timer_diff(self) -> int:
        return (datetime.utcnow() - self.last).seconds

    def _heartbeat_check(self) -> bool:
        return self._hb_timer_diff() < 5

    async def _next_heartbeat(self, delay: int) -> None:
        await asyncio.sleep(delay)

        hb = HeartbeatLetter(self._infos['hostname'], self.hbCount)

        try:
            await sending(self.writer, hb)
        except ConnectionError:
            # Just return
            # that link will be rebuild while timer
            # timeout in wrost situation.
            return
        except Exception:
            traceback.print_exc()

    async def _connectability_check_proc(
            self, hbEvent: HeartbeatLetter) -> None:

        seq = hbEvent.getSeq()

        if self.hbCount != seq:
            return

        self.hbCount += 1

        if self._isActive:
            self._loop.create_task(self._next_heartbeat(2))
        else:
            hbEvent.setIdent(self._infos['hostname'])
            await sending(self.writer, hbEvent)

    def start(self) -> None:
        if self._isActive:
            self._loop.create_task(self._hb_begin())
        else:
            self._loop.create_task(self.run())

    def stop(self) -> None:
        self.writer.close()
        self.state = Link.REMOVED

    async def _hb_begin(self) -> None:
        try:
            # First heartbeat is begin from the side open the connection.
            await sending(
                self.writer,
                HeartbeatLetter(self._infos['hostname'], 0)
            )
        except (ConnectionError, BrokenPipeError):
            # Failed to send heartbeat link should not to run
            # in this situation.
            await self.notify("LinkLost", self.ident)
            return

        # Hb is transfer success link is ready to process letters.
        self._loop.create_task(self.run())

    async def run(self) -> None:
        try:
            await self.run_internal()
        except (ConnectionError, ConnectionResetError, BrokenPipeError):
            await self.notify("LinkLost", self.ident)

    async def run_internal(self) -> None:

        assert(self._dispatch_proc is not None)

        while True:

            if self.state == Link.REMOVED or self._heartbeat_check() is False:
                await self.notify("LinkLost", self.ident)
                return

            try:
                letter = await receving(self.reader, timeout=3)
                if letter is None:
                    continue
            except asyncio.exceptions.TimeoutError:
                continue

            if isinstance(letter, HeartbeatLetter):
                self._hb_timeer_udpate()
                await self._connectability_check_proc(letter)
            else:
                await self._dispatch_proc(letter)

    async def sendletter(self, letter: Letter) -> None:
        await sending(self.writer, letter, lock=self._lock)
