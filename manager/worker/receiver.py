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

# receiver.py

from ..basic.mmanager import ModuleDaemon
from .server import Server
from .processor import Processor

from ..basic.info import Info

from multiprocessing import Pool

from typing import Any, Dict, List

from manager.worker.processor import M_NAME as PROCESSOR_M_NAME

import traceback

M_NAME = "Recevier"


class Receiver(ModuleDaemon):

    def __init__(self, server: Server, info: Info, cInst: Any) -> None:
        global M_NAME
        ModuleDaemon.__init__(self, M_NAME)

        self.server = server
        self.max = int(info.getConfig('MAX_TASK_CAN_PROC'))
        self.numOfTasksInProc = 0
        self.pool = Pool(int(info.getConfig('PROCESS_POOL_SIZE')))
        self.info = info
        self.inProcTasks = {}  # type: Dict[str, Any]
        self._status = 0
        self._cInst = cInst

    def begin(self) -> None:
        return None

    def cleanup(self) -> None:
        return None

    def numOfTasks(self) -> int:
        return self.numOfTasksInProc

    def maxNumber(self) -> int:
        return self.max

    def stop(self) -> None:
        self._status = 1

    def status(self) -> int:
        return self._status

    def listOfTasks(self) -> List[Any]:
        return list(self.inProcTasks.values())

    def listOfTasks_ident(self) -> List[str]:
        return list(self.inProcTasks.keys())

    def run(self) -> None:

        server = self.server
        processor = self._cInst.getModule(PROCESSOR_M_NAME)

        # Not Processor module
        if not isinstance(processor, Processor):
            raise Exception

        while True:

            if self._status == 1:
                return None

            try:
                reqLetter = server.waitLetter()

                processor.recyle()

                if isinstance(reqLetter, int):

                    if reqLetter == Server.SOCK_DISCONN:
                        continue
                    elif reqLetter == Server.SOCK_TIMEOUT:
                        continue
                    elif reqLetter == Server.SOCK_PARSE_ERROR:
                        continue

                else:
                    print(reqLetter.toString())
                    processor.proc(reqLetter)

            except Exception:
                traceback.print_exc()
