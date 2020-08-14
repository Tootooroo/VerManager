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

# post

from typing import Any, Union

from ..basic.info import Info
from ..basic.type import State
from ..basic.letter import Letter
from ..basic.mmanager import Module

from .server import Server


class Post(Module):
    def __init__(self, address: str, port: int, info: Info, cInst: Any) -> None:
        Module.__init__(self, "")
        self._server = Server(address, port, info, cInst)

    def connect(self, workerName: str) -> State:
        return self._server.connect()

    def disconnect(self) -> None:
        self._server.disconnect()

    def setSockTimeout(self, t: int) -> None:
        self._server.setSockTimeout(t)

    def waitLetter(self) -> Union[int, Letter]:
        return self._server.waitLetter()

    def transfer(self, letter: Letter) -> None:
        self._server.transfer(letter)

    def transfer_step(self, timeout: int = None) -> int:
        return self._server.transfer_step(timeout)

    def reconnect(self, workerName: str, max: int, proc: int) -> State:
        return self._server.reconnect()
