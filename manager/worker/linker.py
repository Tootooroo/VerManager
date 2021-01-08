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
from manager.basic.letter import Letter, receving, PropLetter
from manager.worker.exceptions import LINK_NOT_EXISTS
from manager.basic.info import Info


DispatchProc = T.Callable[[Letter], T.Coroutine]


class Linker(Observer):

    def __init__(self, dispatch_proc: DispatchProc) -> None:
        assert(share.config is not None)

        Observer.__init__(self)
        self._links = {}  # type: T.Dict[str, Link]
        self._dispatch_proc = dispatch_proc

        # Format of keys of _listener is host:port, which type is str
        self._listener = {}  # type: T.Dict[str, T.Any]
        self._config = T.cast(Info, share.config)

    async def createLink(self, linkid: str, host: str, port: int) -> None:
        """
        Create a link which id is linkid, if already exists just return
        """
        if linkid in self._links:
            return

        r, w = await asyncio.open_connection(host=host, port=port)
        link = HBLink(
            linkid, host, port, r, w,
            {'hostname': self._config.getConfig('WORKER_NAME')},
            isActiveSide=True
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
        if linkid in self._links:
            return self._links[linkid].state
        else:
            return None

    async def sendOnLink(self, linkid: str, letter: Letter) -> None:
        if linkid not in self._links:
            raise LINK_NOT_EXISTS(linkid)
        link = self._links[linkid]
        await link.sendletter(letter)

    async def createListener(self, host: str, port: int) -> None:
        """
        Create a listener listen on given address. If already exists
        just return.
        """
        key = host + ":" + str(port)
        if key in self._listener:
            return None

        # Create server
        server = await asyncio.start_server(
            self._link_create_cb,
            host=host,
            port=port
        )
        asyncio.get_running_loop()\
            .create_task(server.serve_forever())

        self._listener[key] = server

    async def deleteListener(self, host: str, port: int) -> None:
        """
        Stop and delete a listener
        """
        key = host + ":" + str(port)
        if key not in self._listener:
            return

        self._listener[key].close()
        del self._listener[key]

    def exists(self, linkid: str) -> bool:
        return linkid in self._links

    def dispatch_proc(self) -> T.Callable:
        return self._dispatch_proc

    async def _link_create_cb(
            self,
            r: asyncio.StreamReader,
            w: asyncio.StreamWriter,) -> None:

        prop = T.cast(PropLetter, await receving(r))
        if prop is None:
            return

        ident = prop.getIdent()
        link = HBLink(
            ident, "", 0, r, w,
            {'hostname': self._config.getConfig('WORKER_NAME')}
        )
        link.setDispatchProc(self._dispatch_proc)
        link.start()
        self._links[ident] = link

    async def _maintain(self) -> None:
        pass
