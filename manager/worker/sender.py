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

        self._status = 0

        self._send_rtns = [] # type: List[SendRtn_NoWait_NoExcep]

    def stop(self) -> None:
        self._status = 1

    def rtnRegister(self, rtn:SendRtn_NoWait_NoExcep) -> State:
        if rtn in self._send_rtns:
            return Error

        self._send_rtns.append(rtn)
        return Ok

    def rtnUnRegister(self, rtn:SendRtn_NoWait_NoExcep) -> State:
        if rtn in self._send_rtns:
            self._send_rtns.remove(rtn)

        return Ok

    def run(self) -> None:
        cond = self.cond

        cond.acquire()

        last = datetime.utcnow()
        isIdle = lambda now,last: (now - last).seconds > 3

        while True:
            if self._status == 1:
                self._status = 2
                cond.release()
                return None

            now = datetime.utcnow()

            for rtn in self._send_rtns:
                if rtn() is Ok: last = now

            if isIdle(now, last):
                time.sleep(1)
