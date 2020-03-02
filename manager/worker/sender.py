# sender.py

import time

import typing
from ..basic.mmanager import ModuleDaemon
from ..basic.info import Info
from ..basic.type import *
from .server import Server

from threading import Condition

M_NAME = "Sender"

class Sender(ModuleDaemon):

    def __init__(self, server:Server, info:Info, cInst:typing.Any) -> None:
        global M_NAME
        ModuleDaemon.__init__(self, M_NAME)

        self.cond = Condition()
        self.server = server

        self.__status = 0

    def stop(self) -> None:
        self.__status = 1

    def run(self) -> None:
        cond = self.cond
        server = self.server

        cond.acquire()

        while True:
            if self.__status == 1:
                self.__status = 2
                cond.release()
                return None

            try:
                ret = server.transfer_step(1)
            except:
                continue

            while ret == Error:
                # Waiting for <Receiver> reconnecting
                time.sleep(5)
                continue
