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
import typing as T
import manager.master.proxy_configs as P
import client.client as C
from manager.basic.mmanager import ModuleDaemon
from manager.master.msgCell import MsgUnit, MsgSource, MsgWrapper


class Proxy(ModuleDaemon):

    M_NAME = "Proxy"

    def __init__(self, q_size: int) -> None:
        ModuleDaemon.__init__(self, self.M_NAME)

        self._msg_units = {}  # type: T.Dict[str, T.List[MsgUnit]]
        self._q = asyncio.Queue(q_size)  # type: asyncio.Queue[MsgWrapper]

    async def begin(self) -> None:
        return None

    async def cleanup(self) -> None:
        return None

    def add_msg_source(self, msg_type: str, src: MsgSource,
                       config: T.Dict[str, str]) -> None:
        if msg_type not in self._msg_units:
            self._msg_units[msg_type] = []

        # Setup q
        src.setQ(self._q)

        unit = MsgUnit(msg_type, src, {})
        self._msg_units[msg_type].append(unit)

    def del_msg_source(self, msg_type: str, src_id: str) -> None:
        if msg_type not in self._msg_units:
            return None

        units = self._msg_units[msg_type]
        self._msg_units[msg_type] = [
            unit for unit in units if unit.src_id() != src_id
        ]

    async def real_time_notify_proc(self) -> None:
        while True:
            wrapper = await self._q.get()  # type: MsgWrapper

            # Apply config
            msg, who = P.ProxyConfigs.apply(
                wrapper.config_map, wrapper.msg)

            for client_name in who:
                await C.clients[client_name].notify(msg)

    async def period_notify_proc(self) -> None:
        return None

    async def run(self) -> None:
        await asyncio.gather(
            self.real_time_notify_proc(),
            self.period_notify_proc()
        )
