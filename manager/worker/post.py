# post

from typing import Any, Union

from ..basic.info import Info
from ..basic.type import *
from ..basic.letter import Letter
from ..basic.mmanager import Module

from .server import Server

class Post(Module):
    def __init__(self, address:str, port:int, info:Info, cInst:Any) -> None:
        Module.__init__(self, "")
        self._server = Server(address, port, info, cInst)

    def connect(self, workerName:str) -> State:
        return self._server.connect()

    def disconnect(self) -> None:
        self._server.disconnect()

    def setSockTimeout(self, t:int) -> None:
        self._server.setSockTimeout(t)

    def waitLetter(self) -> Union[int, Letter]:
        return self._server.waitLetter()

    def transfer(self, letter:Letter) -> None:
        self._server.transfer(letter)

    def transfer_step(self, timeout:int = None) -> int:
        return self._server.transfer_step(timeout)

    def reconnect(self, workerName:str, max:int, proc:int) -> State:
        return self._server.reconnect()
