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
import typing as T
from client.messages import Message
from manager.master.exceptions import UNABLE_SEND_MSG_TO_PROXY, \
    MSG_WRAPPER_CFG_NOT_EXISTS


class MsgWrapper:

    ON = 'on'
    OFF = 'off'

    def __init__(self, msg: Message) -> None:
        self.msg = msg
        self._config_map = {}  # type: T.Dict[str, str]

    def get_msg(self) -> Message:
        return self.msg

    def add_config(self, cfg_key: str) -> None:
        """
        Add config in to config_map if the config is already
        exists, just cover it.
        """
        self._config_map[cfg_key] = MsgWrapper.ON

    def add_config_off(self, cfg_key: str) -> None:
        """
        Similar to add_config but it's default value
        is OFF.
        """
        self._config_map[cfg_key] = MsgWrapper.OFF

    def set_config_on(self, cfg_key: str) -> None:
        try:
            self._config_map[cfg_key] = MsgWrapper.ON
        except KeyError:
            raise MSG_WRAPPER_CFG_NOT_EXISTS(cfg_key)

    def set_config_off(self, cfg_key: str) -> None:
        try:
            self._config_map[cfg_key] = MsgWrapper.OFF
        except KeyError:
            raise MSG_WRAPPER_CFG_NOT_EXISTS(cfg_key)

    def is_turn_on(self, config_key: str) -> bool:
        return config_key in self._config_map and \
            self._config_map[config_key] == MsgWrapper.ON

    def get_config(self, config_key: str) -> T.Optional[str]:
        if config_key not in self._config_map:
            return None
        return self._config_map[config_key]


class MsgSource(abc.ABC):

    def __init__(self, src_id: str) -> None:
        self.src_id = src_id

        # Used by sendMsg to transfer message to
        # Proxy, seted by Proxy while added to Proxy.
        self._q = None  # type: T.Optional[asyncio.Queue]

    def real_time_msg(self, msg: Message, is_broadcast: bool) -> None:
        """
        Wrap a message into a MsgWrapper with control info then
        send the MsgWrapper to Proxy
        """
        wrapper = MsgWrapper(msg)

        try:

            if self._q is not None:
                self._q.put_nowait(msg)

        except asyncio.QueueFull:
            raise UNABLE_SEND_MSG_TO_PROXY(
                "Proxy's message queue is full"
            )

    def real_time_msg_available(self) -> bool:
        return self._q is not None and not self._q.full()

    @abc.abstractmethod
    async def gen_msg(self) -> T.Optional[Message]:
        """
        Generate Message

        Require: noblocked, noexcept
        """


class MsgUnit:

    def __init__(self, msg_type: str, source: MsgSource) -> None:
        self._type = msg_type
        self._source = source

    def src_id(self) -> str:
        return self._source.src_id

    def msg_type(self) -> str:
        return self._type

    async def gen_msg(self) -> T.Optional[Message]:
        return await self._source.gen_msg()
