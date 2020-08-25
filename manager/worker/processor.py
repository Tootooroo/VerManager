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
import typing
import asyncio

import manager.basic.commands as CMDS
from manager.worker.procUnit \
    import ProcUnit, PROC_UNIT_HIGHT_OVERLOAD, PROC_UNIT_IS_IN_DENY_MODE
from manager.basic.mmanager import ModuleDaemon
from manager.basic.letter import Letter, CommandLetter


class Dispatcher:

    def __init__(self) -> None:
        self._units = {}  # type: typing.Dict[str, ProcUnit]

    def addUnit(self, type: str, unit: ProcUnit) -> None:
        if type in self._units:
            return None
        self._units[type] = unit

    def dispatch(self, cl: Letter) -> None:
        type = cl.__name__  # type: ignore

        if type not in self._units:
            raise PROCESSOR_DISPATCHE_CANT_FIND_THE_TYPE(type)

        # These two exception will be dealt by UnitMaintainer.
        # Dispatcher is focus on work of dispatch.
        try:
            self._units[type].proc(cl)
        except (PROC_UNIT_HIGHT_OVERLOAD, PROC_UNIT_IS_IN_DENY_MODE):
            pass


class Output:

    def __init__(self) -> None:
        self.outputQ = asyncio.Queue(256)  # type: asyncio.Queue


class Channel:

    def __init__(self) -> None:
        self._channels = {}  # type: typing.Dict

    def addChannel(self, ident: str) -> typing.Dict:
        if ident in self._channels:
            raise PROCESSOR_UNIT_CHANNEL_EXISTS()

        new_channel = {}  # type: typing.Dict
        self._channels[ident] = new_channel

        return new_channel

    def getChannel(self, ident: str) -> typing.Optional[typing.Dict]:
        if ident not in self._channels:
            return None
        return self._channels[ident]

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

    def msgLen(self, uid: str) -> int:
        if uid in self.channel_data:
            return len(self.channel_data[uid])
        return 0

    @abc.abstractmethod
    def update(self, uid: str) -> None:
        """ Be called while infor is updated """


class UnitMaintainer(ChannelReceiver):

    def __init__(self, ucontainer: typing.Dict) -> None:
        ChannelReceiver.__init__(self)
        self._states = {}  # type: typing.Dict[str, int]
        self._units = ucontainer

    def update(self, uid: str) -> None:
        info = self.last(uid)
        if info is None:
            return None
        self._maintain(uid, info)

    def addTrack(self, uid: str, msgSrc: typing.Dict) -> None:
        ChannelReceiver.addTrack(self, uid, msgSrc)

        # Update _states
        info = self.last(uid)
        if info is not None:
            self._states[uid] = info['state']

    def _maintain(self, uid: str, info: typing.Dict) -> None:
        state = info['state']

        # Fixme: Should also to notify master what happened.
        if state == ProcUnit.STATE_OVERLOAD:
            self._states[uid] = ProcUnit.STATE_OVERLOAD
        elif state == ProcUnit.STATE_DENY:
            self._states[uid] = ProcUnit.STATE_DENY
        elif state == ProcUnit.STATE_STOP:
            # Restart the ProcUnit
            unit = self._units[uid]
            asyncio.get_running_loop()\
                   .create_task(self.unitRestart(unit))
            self._states[uid] = ProcUnit.STATE_STOP

    @staticmethod
    async def unitRestart(unit: ProcUnit) -> None:
        # Prevent exhaust resources in some cases
        await asyncio.sleep(10)
        unit.start()


class Processor(ModuleDaemon):

    NAME = "Processor"
    CMDHandler = typing.Callable[[CommandLetter], typing.Coroutine]

    def __init__(self) -> None:
        ModuleDaemon.__init__(self, self.NAME)

        self._unit_container = {}  # type: typing.Dict[str, ProcUnit]
        self._maintainer = UnitMaintainer(self._unit_container)
        self._channel = Channel()
        self._t = None  # type: typing.Optional[asyncio.Task]
        self._dispatcher = Dispatcher()
        self._reqQ = asyncio.Queue(256)  # type: asyncio.Queue[Letter]
        self._output = Output()

    async def begin(self) -> None:
        return None

    async def cleanup(self) -> None:
        return None

    def req(self, letter: Letter) -> None:
        self._reqQ.put_nowait(letter)

    def install_unit(self, unit: ProcUnit) -> None:
        uid = unit.ident()
        if uid in self._unit_container:
            raise PROCESSOR_UNIT_ALREADY_EXISTS(uid)
        self._unit_container[uid] = unit

        # Setup channel for unit
        channel = self._channel.addChannel('uid')
        unit.setChannel(channel)

        # Setup output space for unit
        unit.setOutput(self._output.outputQ)

    async def run(self) -> None:
        letter = await self._reqQ.get()

        # Deal with CommandLetter
        if isinstance(letter, CommandLetter):
            await self.CMD_Proc(letter)
        else:
            # If not a CommandLetter then dispatch to
            # ProcUnit
            self._dispatcher.dispatch(letter)

    def register(self, uid: str, comp: ChannelReceiver) -> None:
        if self._channel.isChannelExists(uid):
            msgSrc = self._channel.getChannel(uid)
            if msgSrc is not None:
                comp.addTrack(uid, msgSrc)

    #################################################
    # Section of methods that for command deal with.#
    #################################################

    # CMD process entry
    async def CMD_Proc(self, cl: CommandLetter) -> None:
        type = cl.getType().upper()

        h = self.CMD_MATCH(type)
        if h is None:
            return None

        await h(self, cl)

    def CMD_MATCH(self, type) -> typing.Optional[typing.Callable]:
        try:
            return getattr(self, 'CMD_H_'+type)
        except AttributeError:
            return None

    async def CMD_H_ACCEPT(self, cl: CommandLetter) -> None:
        """ Master is accept this worker """
        return None

    async def CMD_H_ACCEPT_RST(self, cl: CommandLetter) -> None:
        return None


class PROCESSOR_UNIT_ALREADY_EXISTS(Exception):

    def __init__(self, uid: str) -> None:
        self.uid = uid

    def __str__(self) -> str:
        return "Unit " + self.uid + " is already exists"


class PROCESSOR_UNIT_CHANNEL_EXISTS(Exception):
    pass


class PROCESSOR_DISPATCHE_CANT_FIND_THE_TYPE(Exception):

    def __init__(self, type: str) -> None:
        self.type = type

    def __str__(self) -> str:
        return "Dispatcher can't find a unit to process type: " + self.type
