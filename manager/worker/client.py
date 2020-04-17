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

        self._cfgPath = cfgPath

        self._name = name

        self._mAddress = mAddress
        self._mPort = mPort

        self._isStop = True

        self._manager = MManager()

    def getIdent(self) -> str:
        return self._name

    def stop(self) -> None:
        self._manager.stopAll()

    def inProcTasks(self) -> Optional[int]:
        processor = self._manager.getModule(PROCESSOR_M_NAME)

        if isinstance(processor, Processor):
            return processor.tasksInProc()

        return None

    def isStop(self) -> bool:
        return self._isStop

    def connect(self) -> None:
        server = self.getModule(SERVER_M_NAME)
        taskDealer = self.getModule(RECEIVER_M_NAME)

        if server is None or not isinstance(server, Server):
            return None
        if taskDealer is None or not isinstance(taskDealer, Receiver):
            return None

        server.connect()

    def disconnect(self) -> None:
        server = self.getModule(SERVER_M_NAME)
        if server is None or not isinstance(server, Server):
            return None

        server.disconnect()

    def addModule(self, m: Module) -> None:
        self._manager.addModule(m)

    def getModule(self, ident: str) -> Optional[Module]:
        return self._manager.getModule(ident)

    def removeModule(self, ident) -> None:
        self._manager.removeModule(ident)

    def isModuleExists(self, ident: str) -> bool:
        return self._manager.isModuleExists(ident)

    def run(self) -> None:
        self._isStop = False

        info = Info(self._cfgPath)
        self._manager.addModule(info)

        address = self._mAddress
        port = self._mPort

        if self._name == "":
            self._name = workerName = info.getConfig('WORKER_NAME')
        else:
            workerName = self._name

        s = Server(address, port, info, self)
        s.setWorkerName(workerName)
        self._manager.addModule(s)

        m1 = Receiver(s, info, self)
        self._manager.addModule(m1)

        m2 = Sender(s, info, self)
        m2.rtnRegister(lambda : s.transfer_step(1))
        self._manager.addModule(m2)

        m3 = Processor(info, self)
        self._manager.addModule(m3)

        self._manager.startAll()

        # Block the initial thread cause the entire program
        # exists when only daemon-thread exists. initial thread
        # is the only one non-daemon thread.
        self._manager.join()

        print("Stop")
        self._isStop = True


if __name__ == '__main__':
    configPath = sys.argv[1]

    info = Info(configPath)

    address = info.getConfig('MASTER_ADDRESS', 'host')
    port = info.getConfig('MASTER_ADDRESS', 'port')

    client = Client(address, port, configPath)
    client.start()
