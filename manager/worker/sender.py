# sender.py

import time
from datetime import datetime

from typing import Any, Callable, List

from ..basic.mmanager import ModuleDaemon
from ..basic.info import Info
from ..basic.type import *
from .server import Server

from threading import Condition

M_NAME = "Sender"

SendRtn_NoWait_NoExcep = Callable[[], State]

class Sender(ModuleDaemon):

    def __init__(self, server:Server, info:Info, cInst:Any) -> None:
        global M_NAME
        ModuleDaemon.__init__(self, M_NAME)

        self.cond = Condition()
        self.server = server

        self.__status = 0

        self.__send_rtns = [] # type: List[SendRtn_NoWait_NoExcep]

    def stop(self) -> None:
        self.__status = 1

    def rtnRegister(self, rtn:SendRtn_NoWait_NoExcep) -> State:
        if rtn in self.__send_rtns:
            return Error

        self.__send_rtns.append(rtn)
        return Ok

    def rtnUnRegister(self) -> State:
        pass

    def run(self) -> None:
        cond = self.cond

        cond.acquire()

        last = datetime.utcnow()
        isIdle = lambda now,last: (now - last).seconds > 5
        needToUpdate = lambda now,last: (now - last).seconds > 3

        while True:
            if self.__status == 1:
                self.__status = 2
                cond.release()
                return None

            now = datetime.utcnow()
            ret = False

            for rtn in self.__send_rtns:
                ret = ret or rtn() is Ok

                if needToUpdate(now, last):
                    last = now

            if isIdle(now, last):
                time.sleep(1)
