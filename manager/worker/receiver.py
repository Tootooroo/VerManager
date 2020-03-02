# receiver.py

from ..basic.mmanager import ModuleDaemon
from .server import Server
from .processor import Processor

from ..basic.info import Info

from multiprocessing import Pool

from typing import Any, Dict, List

from manager.worker.processor import M_NAME as PROCESSOR_M_NAME

M_NAME = "Recevier"

class Receiver(ModuleDaemon):

    def __init__(self, server:Server, info:Info, cInst:Any) -> None:
        global M_NAME
        ModuleDaemon.__init__(self, M_NAME)

        self.server = server
        self.max = int(info.getConfig('MAX_TASK_CAN_PROC'))
        self.numOfTasksInProc = 0
        self.pool = Pool( int(info.getConfig('PROCESS_POOL_SIZE')) )
        self.info = info
        self.inProcTasks = {} # type: Dict[str, Any]
        self.__status = 0
        self.__cInst = cInst

    def numOfTasks(self) -> int:
        return self.numOfTasksInProc

    def maxNumber(self) -> int:
        return self.max

    def stop(self) -> None:
        self.__status = 1

    def status(self) -> int:
        return self.__status

    def listOfTasks(self) -> List[Any]:
        return list( self.inProcTasks.values())

    def listOfTasks_ident(self) -> List[str]:
        return list( self.inProcTasks.keys())

    def run(self) -> None:

        server = self.server
        processor = self.__cInst.getModule(PROCESSOR_M_NAME)

        # Not Processor module
        if not isinstance(processor, Processor):
            raise Exception

        while True:

            if self.__status == 1:
                return None

            reqLetter = server.waitLetter()

            if isinstance(reqLetter, int):
                continue

            processor.proc(reqLetter)
            processor.recyle()
