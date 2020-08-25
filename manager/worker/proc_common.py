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

from manager.basic.letter import Letter


class Output:

    # Able to transfer data
    STATE_READY = 0

    # Unable to transfer data but
    # ProcUnit can still put data into
    # output space until out of space
    STATE_STOP = 1

    def __init__(self) -> None:
        self._outputQ = asyncio.Queue(256)  # type: asyncio.Queue
        self._state = self.STATE_READY

    def state(self) -> int:
        return self._state

    def ready(self) -> None:
        self._state = self.STATE_READY

    def stop(self) -> None:
        self._state = self.STATE_STOP

    def setState(self, state: int) -> None:
        self._state = state

    def put_nowait(self, letter: Letter) -> None:
        self._outputQ.put_nowait(letter)

    async def put(self, letter: Letter, timeout=None) -> None:
        await asyncio.wait_for(
            self._outputQ.put(letter), timeout=timeout)

    def get_nowait(self) -> None:
        if self.isReady():
            return self._outputQ.get_nowait()
        else:
            raise PROCESSOR_OUTPUT_STOP()

    async def get(self, timeout=None) -> None:
        if self.isReady():
            return await asyncio.wait_for(
                self._outputQ.get(), timeout=timeout)
        else:
            raise PROCESSOR_OUTPUT_STOP()

    def isReady(self) -> bool:
        return self._state == self.STATE_READY

    def isStop(self) -> bool:
        return self._state == self.STATE_STOP


class ChannelEntry:

    def __init__(self, uid: str) -> None:
        self.uid = uid
        self.info = {}  # type: typing.Dict[str, typing.Any]
        self._recvers = []  # type: typing.List[ChannelReceiver]

    def update(self, key: str, val: typing.Any) -> None:
        self.info[key] = val

    async def push(self) -> None:
        for r in self._recvers:
            await r.update(self.uid)

    def addReceiver(self, comp: 'ChannelReceiver') -> None:
        self._recvers.append(comp)


class Channel:

    def __init__(self) -> None:
        self._channels = {}  # type: typing.Dict[str, ChannelEntry]

    def addChannel(self, ident: str) -> ChannelEntry:
        if ident in self._channels:
            raise PROCESSOR_UNIT_CHANNEL_EXISTS()

        new_channel = ChannelEntry(ident)
        self._channels[ident] = new_channel

        return new_channel

    def addReceiver(self, uid: str, comp: 'ChannelReceiver') -> None:
        if uid not in self._channels:
            raise Exception
        self._channels[uid].addReceiver(comp)

    def getChannelData(self, ident: str) -> typing.Optional[typing.Dict]:
        if ident not in self._channels:
            return None
        return self._channels[ident].info

    def isChannelExists(self, uid: str) -> bool:
        return uid in self._channels


class ChannelReceiver(abc.ABC):

    def __init__(self) -> None:
        self.channel_data = {}  # type: typing.Dict[str, typing.Dict]

    def addTrack(self, uid: str, msgSrc: typing.Dict) -> None:
        if uid in self.channel_data:
            return None
        self.channel_data[uid] = msgSrc

    def last(self, uid: str) -> typing.Optional[typing.Dict]:
        if uid in self.channel_data:
            return self.channel_data[uid]
        return None

    @abc.abstractmethod
    async def update(self, uid: str) -> None:
        """ Be called while info is updated """


class PROCESSOR_UNIT_ALREADY_EXISTS(Exception):

    def __init__(self, uid: str) -> None:
        self.uid = uid

    def __str__(self) -> str:
        return "Unit " + self.uid + " is alread installed"


class PROCESSOR_UNIT_CHANNEL_EXISTS(Exception):
    pass


class PROCESSOR_DISPATCHE_CANT_FIND_THE_TYPE(Exception):

    def __init__(self, type: str) -> None:
        self.type = type

    def __str__(self) -> str:
        return "Dispatcher can't find a unit to process type: " + self.type


class PROCESSOR_OUTPUT_STOP(Exception):
    pass
