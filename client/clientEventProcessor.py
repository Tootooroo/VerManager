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

from typing import Dict, Callable, Optional, List
from client.exceptions import EVENT_IS_ALREADY_INSTALLED, \
    EVENT_NOT_FOUND
from client.messages import ClientEvent, Message


class ClientEventProcessor:

    # Callable of PROC_TBL must return a Coroutine.
    PROC_TBL = {}  # type: Dict[str, Callable]

    @classmethod
    def event_proc_install(self, event_type: str, handler: Callable) -> None:
        if event_type in self.PROC_TBL or \
           handler is None:
            raise EVENT_IS_ALREADY_INSTALLED(event_type)

        self.PROC_TBL[event_type] = handler

    @classmethod
    def event_proc_uninstall(self, event_type: str) -> None:
        if event_type not in self.PROC_TBL:
            return None
        del self.PROC_TBL[event_type]

    @classmethod
    def event_proc_exists(self, event_type: str) -> bool:
        return evnet_type in self.PROC_TBL

    @classmethod
    async def proc(self, event: ClientEvent) -> Optional[List[Message]]:

        if event.type not in self.PROC_TBL:
            raise EVENT_NOT_FOUND(event.type)

        return await self.PROC_TBL[event.type](event)
