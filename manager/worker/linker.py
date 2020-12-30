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
import manager.worker.configs as share
from manager.basic.observer import Observer
from manager.worker.link import Link, HBLink
from manager.basic.letter import Letter

class Linker(Observer):

    def __init__(self, dispatch_proc: T.Callable[[Letter], T.Coroutine]) -> None:
        assert(share.config is not None)

        Observer.__init__(self)
        self._links = {}  # type: T.Dict[str, Link]
        self._dispatch_proc = dispatch_proc

    async def createLink(self, linkid: str, host: str, port: int) -> None:
        if linkid in self._links:
            return

        r, w = await asyncio.open_connection(host=host, port=port)
        link = HBLink(
            linkid, host, port, r, w,
            {'hostname': share.config.getConfig('WORKER_NAME')}
        )
        link.setDispatchProc(self._dispatch_proc)
        link.start()

        self._links[linkid] = link

    def deleteLink(self, linkid: str) -> None:
        if linkid not in self._links:
            return None

        link = self._links[linkid]
        link.stop()

        del self._links[linkid]

    def linkState(self, linkid: str) -> T.Optional[int]:
        if linkid not in self._links:
            return self._links[linkid].state

    async def sendOnLink(self, linkid: str, letter: Letter) -> None:
        pass

    def createListener(self, host: str, port: str) -> None:
        pass

    def exists(self, linkid: str) -> bool:
        return linkid in self._links
