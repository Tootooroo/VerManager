# processor.py

import time

from typing import Any, Optional, Callable, List, Tuple, Dict
from multiprocessing import Pool
from multiprocessing.pool import AsyncResult

from ..basic.letter import *
from ..basic.info import Info
from ..basic.type import *
from ..basic.util import partition

from ..basic.mmanager import Module

from .post import Post
from .server import Server
from .postListener import PostListener, PostProvider

from ..basic.commands import Command, PostConfigCmd, CMD_CONFIG_TYPE, CMD_POST_SUBTYPE

Procedure = Callable[[Server, Post, Letter, Info], None]

CommandHandler = Callable[[CommandLetter, Info, Any], State]

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

    def proc(self, reqLetter:Letter) -> None:

        # fixme: need to deal with exception of command or
        #        newtask
        if isinstance(reqLetter, CommandLetter):
            self.proc_command(reqLetter)
        elif isinstance(reqLetter, NewLetter):
            self.proc_newtask(reqLetter)

    def proc_command(self, cmdLetter:CommandLetter) -> State:

        cmd = Command.fromLetter(cmdLetter)

        type = cmdLetter.getHeader('type')
        subType = cmdLetter.getHeader('extra')

        if type not in cmdHandlers:
            return Error

        handlers = cmdHandlers[type]

        if subType not in handlers:
            return Error

        handler = handlers[subType]

        return handler(cmdLetter, self.__info, self.__cInst)

    @staticmethod
    def post_config(cmdLetter:CommandLetter, info:Info, cInst:Any) -> State:

        cmd = PostConfigCmd.fromLetter(cmdLetter)

        if cmd is None:
            return Error

        (address, port) = cmd.address()

        role = cmd.role()

        if role is PostConfigCmd.ROLE_LISTENER:
            return Processor.__postListener_config(address, port, info, cInst)
        elif role is PostConfigCmd.ROLE_PROVIDER:
            return Processor.__postProvider_config(address, port, info, cInst)

        return Error

    @staticmethod
    def __postListener_config(address:str, port:int, info:Info, cInst:Any) -> State:
        pl = PostListener(address, port, cInst)
        pl.start()

        cInst.addModule(pl)

        return Ok

    @staticmethod
    def __postProvider_config(address:str, port:int, info:Info, cInst:Any) -> State:
        provider = PostProvider(address, port)

        # PostConfigCmd will send from master to the worker
        # which role is listener and workers
        # that role is provider at the same
        # time so command to provider may arrived before command
        # to listener arrived. Give retry chance here to make sure
        # provider is able to connect to listener.
        retry = 3

        while retry > 0:
            if provider.connectToListener() is Ok:
                break
            time.sleep(1)

        cInst.addModule(provider)
        return Ok

    def proc_newtask(self, reqLetter:NewLetter) -> State:

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


cmdHandlers = {
    CMD_CONFIG_TYPE: {CMD_POST_SUBTYPE: Processor.post_config}
} # type: Dict[str, Dict[str, CommandHandler]]
