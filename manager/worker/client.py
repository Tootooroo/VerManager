# server.py
# Usage: python server.py <configPath>

import sys
import os
import platform

from threading import Thread
from typing import Union, List, Optional

from ..basic.letter import Letter, ResponseLetter, BinaryLetter
from ..basic.info import Info
from ..basic.mmanager import MManager, Module

from .processor import Processor
from .sender import Sender
from .receiver import Receiver
from .server import Server
from .post import Post

from .server import M_NAME as SERVER_M_NAME
from .receiver import M_NAME as RECEIVER_M_NAME
from .processor import M_NAME as PROCESSOR_M_NAME

class Client(Thread):

    def __init__(self, mAddress: str,
                 mPort: int, cfgPath: str,
                 name: str = "") -> None:

        Thread.__init__(self)

        self.__cfgPath = cfgPath

        self.__name = name

        self.__mAddress = mAddress
        self.__mPort = mPort

        self.__isStop = True

        self.__manager = MManager()

    def getIdent(self) -> str:
        return self.__name

    def stop(self) -> None:
        self.__manager.stopAll()

    def inProcTasks(self) -> Optional[int]:
        processor = self.__manager.getModule(PROCESSOR_M_NAME)

        if isinstance(processor, Processor):
            return processor.tasksInProc()

        return None

    def isStop(self) -> bool:
        return self.__isStop

    def connect(self) -> None:
        server = self.getModule(SERVER_M_NAME)
        taskDealer = self.getModule(RECEIVER_M_NAME)

        if server is None or not isinstance(server, Server):
            return None
        if taskDealer is None or not isinstance(taskDealer, Receiver):
            return None

        server.connect(self.__name, taskDealer.maxNumber(),
                       taskDealer.numOfTasks())

    def disconnect(self) -> None:
        server = self.getModule(SERVER_M_NAME)
        if server is None or not isinstance(server, Server):
            return None

        server.disconnect()

    def addModule(self, m: Module) -> None:
        self.__manager.addModule(m)

    def getModule(self, ident: str) -> Optional[Module]:
        return self.__manager.getModule(ident)

    def run(self) -> None:
        self.__isStop = False

        info = Info(self.__cfgPath)
        self.__manager.addModule(info)

        address = self.__mAddress
        port = self.__mPort

        if self.__name == "":
            self.__name = workerName = info.getConfig('WORKER_NAME')
        else:
            workerName = self.__name

        max = info.getConfig('MAX_TASK_CAN_PROC')
        proc = info.getConfig('PROCESS_POOL_SIZE')

        s = Server(address, port, info, self)
        s.connect(workerName, max, proc, retry=3)
        self.__manager.addModule(s)

        m1 = Receiver(s, info, self)
        self.__manager.addModule(m1)

        m2 = Sender(s, info, self)
        self.__manager.addModule(m2)

        m3 = Processor(info, self)
        self.__manager.addModule(m3)

        self.__manager.startAll()

        # Block the initial thread cause the entire program
        # exists when only daemon-thread exists. initial thread
        # is the only one non-daemon thread.
        self.__manager.join()

        self.__isStop = True


if __name__ == '__main__':
    configPath = sys.argv[1]

    info = Info(configPath)

    address = info.getConfig('MASTER_ADDRESS', 'host')
    port = info.getConfig('MASTER_ADDRESS', 'port')

    client = Client(address, port, configPath)
    client.start()
