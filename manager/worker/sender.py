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

# sender.py

import time
from datetime import datetime

from typing import Any, Callable, List

from ..basic.mmanager import ModuleDaemon
from ..basic.info import Info
from ..basic.type import State, Error, Ok
from .type import SEND_STATE, SEND_STATES

from threading import Condition

M_NAME = "Sender"

SendRtn_NoWait_NoExcep = Callable[[], State]


class SEND_RTN:

    def __init__(self, rtn: SendRtn_NoWait_NoExcep, intvl: int) -> None:
        self._rtn = rtn
        self._able = True
        self._last = datetime.utcnow()
        self._intvl = intvl

    def _isAbleToSend(self) -> bool:
        if self._able is True:
            return True
        else:
            intvl = (datetime.utcnow() - self._last).seconds
            return intvl >= self._intvl

    def rtn(self) -> SendRtn_NoWait_NoExcep:
        return self._rtn

    def execute(self, time=None) -> SEND_STATE:
        if self._isAbleToSend():
            ret = self._rtn()

            self._able = \
                ret is SEND_STATES.NO_DATA or \
                ret is SEND_STATES.DATA_SENDED

            if time is not None:
                self._last = time

            return ret

        else:
            return False


class Sender(ModuleDaemon):

    def __init__(self, info: Info, cInst: Any) -> None:
        global M_NAME
        ModuleDaemon.__init__(self, M_NAME)

        self.cond = Condition()

        self._status = 0

        self._send_rtns = []  # type: List[SEND_RTN]

    def begin(self) -> None:
        return None

    def cleanup(self) -> None:
        return None

    def stop(self) -> None:
        self._status = 1

    def rtnRegister(self, rtn: SendRtn_NoWait_NoExcep) -> State:
        if rtn in self._send_rtns:
            return Error

        self._send_rtns.append(SEND_RTN(rtn, 5))
        return Ok

    def rtnUnRegister(self, rtn: SendRtn_NoWait_NoExcep) -> State:
        if rtn in self._send_rtns:
            self._send_rtns = [r for r in self._send_rtns if rtn != r.rtn()]

        return Ok

    def run(self) -> None:
        cond = self.cond

        cond.acquire()

        last = datetime.utcnow()
        isIdle = lambda now, last: (now - last).seconds > 1

        while True:
            if self._status == 1:
                self._status = 2
                cond.release()
                return None

            now = datetime.utcnow()

            for rtn in self._send_rtns:
                ret = rtn.execute(now)

                if ret == SEND_STATES.DATA_SENDED:
                    last = now

            if isIdle(now, last):
                time.sleep(1)
