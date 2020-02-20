# sender.py

import time

import typing
from module import ModuleT
from basic.info import Info
from basic.type import *
from server import Server

from threading import Condition

class Sender(ModuleT):

    def __init__(self, server:Server, info:Info, cInst:typing.Any) -> None:
        ModuleT.__init__(self)

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
