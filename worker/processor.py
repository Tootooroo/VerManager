# processor.py

from typing import Any, Optional, Callable, List, Tuple, Dict
from multiprocessing import Pool
from multiprocessing.pool import AsyncResult

from .basic.letter import Letter, NewLetter
from .basic.info import Info
from .basic.type import *
from .basic.util import partition

from .basic.mmanager import Module

from .post import Post
from .server import Server

Procedure = Callable[[Server, Post, Letter, Info], None]

class Processor(Module):

    def __init__(self, info:Info, cInst:Any, procedure:Procedure = None) -> None:
        self.__max = int(info.getConfig('MAX_TASK_CAN_PROC'))
        self.__numOfTasksInProc = 0
        self.__cInst = cInst
        self.__poolSize = int(info.getConfig('PROCESS_POLL_SIZE'))
        self.__pool = Pool(self.__poolSize)
        self.__info = info

        self.__procedure = None # type: Optional[Callable]

        # (tid, parent, result)
        self.__allTasks = [] # type: List[Tuple[str, str, AsyncResult]]

        # Query purpose
        self.__allTasks_dict = {} # type: Dict[str, AsyncResult]

    def maxTasksAbleToProc(self) -> int:
        return self.__max

    def tasksInProc(self) -> int:
        return self.__numOfTasksInProc

    def poolSize(self) -> int:
        return self.__poolSize

    def setProcedure(self, procedure:Callable[[Server, Letter, Info], None]) -> None:
        self.__procedure = procedure

    def proc(self, reqLetter:Letter) -> State:

        if not self.isAbleToProc():
            return Error

        tid = reqLetter.getHeader('tid')
        parent = reqLetter.getHeader('parent')

        if self.isReqInProc(tid, parent):
            return Error

        s = self.__cInst.getModule("Server")

        if self.__procedure is None:
            return Error

        res = self.__pool.apply_async(self.__procedure, (s, reqLetter, self.__info))
        self.__numOfTasksInProc += 1

        self.__allTasks.append((tid, parent, res))
        self.__allTasks_dict[parent+tid] = res

        return Ok

    # Remove tasks from processor and return
    # the number of request finished
    def recyle(self) -> int:
        (readies, not_readies) = partition(self.__allTasks, lambda res: res[1].ready())
        self.__allTasks = not_readies

        for res in readies:
            tid = res[0]
            parent = res[1]

            del self.__allTasks_dict [parent+tid]

        return len(readies)

    def isReqInProc(self, tid:str, parent:str = "") -> bool:
        return tid in self.__allTasks_dict

    def isAbleToProc(self) -> bool:
        return self.tasksInProc() < self.maxTasksAbleToProc()
