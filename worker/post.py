# post

from typing import Any, Union

from basic.info import Info
from basic.type import *
from basic.letter import Letter

from module import Module
from server import Server

class Post(Module):

    def __init__(self, address:str, port:int, info:Info, cInst:Any) -> None:
        self.__server = Server(address, port, info, cInst)

    def connect(self, workerName:str) -> State:
        return self.__server.connect(workerName, 0, 0)

    def disconnect(self) -> None:
        self.__server.disconnect()

    def setSockTimeout(self, t:int) -> None:
        self.__server.setSockTimeout(t)

    def waitLetter(self) -> Union[int, Letter]:
        return self.__server.waitLetter()

    def transfer(self, letter:Letter) -> None:
        self.__server.transfer(letter)

    def transfer_step(self, timeout:int = None) -> int:
        return self.__server.transfer_step(timeout)

    def reconnect(self, workerName:str, max:int, proc:int) -> State:
        return self.__server.reconnect(workerName, max, proc)
