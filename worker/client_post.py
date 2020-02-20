# client_post.py

from client import Client
from server import Server
from post import Post
from receiver import Receiver
from sender import Sender
from processor import Processor

from basic.letter import Letter
from basic.info import Info
from basic.mmanager import MManager, ModuleDaemon, Module, ModuleName

from typing import Optional, Any
from threading import Thread

import socket

class PostListener(ModuleDaemon):

    def __init__(self, address:str, port:int, cInst:Any) -> None:
        ModuleDaemon.__init__(self, "")

        self.__address = address
        self.__port = port

    def run(self) -> None:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((self.__address, self.__port))
        s.listen(10)

        while True:
            (wSock, addr) = s.accept()

            proc = PostProcessor(wSock)
            proc.start()


class PostProcessor(Thread):

    def __init__(self, wSock:socket.socket) -> None:
        Thread.__init__(self)

        self.__wSock = wSock

    def run(self) -> None:
        pass


def serverCmdProc(server:Server, post:Post, letter:Letter, info:Info) -> None:
    pass

class Client_Post(Client):

    def __init__(self, mAddress:str, mPort:int, cfgPath:str, name:str = "") -> None:
        Client.__init__(self, mAddress, mPort, cfgPath, name)

    def init(self) -> None:
        info = Info(self.__cfgPath)

        address = self.__mAddress
        port = self.__mPort

        if self.__name == "":
            self.__name = workerName = info.getConfig('WORKER_NAME')
        else:
            workerName = self.__name

        s = Server(address, port, info, self)
        s.connect(workerName, 0, 0)
        self.__manager.addModule("Server", s)

        r = Receiver(s, info, self)
        self.__manager.addModule("Receiver", r)

        sender = Sender(s, info, self)
        self.__manager.addModule("Sender", sender)

        p = Processor(info, self, procedure = serverCmdProc)
        self.__manager.addModule("Processor", p)

        postListener = PostListener("127.0.0.1", 8012, self)
        self.__manager.addModule("PostListener", postListener)

        self.__manager.startAll()

    def getModule(self, mName:str) -> Optional[Module]:
        return self.__manager.getModule(mName)

    def stop(self) -> None:
        self.__manager.stopAll()


if __name__ == '__main__':
    pass
