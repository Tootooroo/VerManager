# processor.py

import time
import os
import traceback
import platform

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

from ..basic.commands import Command, PostConfigCmd, CMD_POST_TYPE

from manager.worker.server import M_NAME as SERVER_M_NAME
from manager.worker.postListener import M_NAME as POST_LISTENER_M_NAME
from manager.worker.postListener import M_NAME_Provider as POST_PROVIDER_M_NAME

from manager.basic.commands import CMD_POST_TYPE

Procedure = Callable[[Server, Post, Letter, Info], None]
CommandHandler = Callable[[CommandLetter, Info, Any], State]

M_NAME = "Processor"

if platform.system() == 'Windows':
    sep = "\\"
else:
    sep = "/"

class Result:

    def __init__(self, tid:str, mid:str,
                 filePath:str, needPost:str,
                 version:str, isSuccess:bool) -> None:
        self.tid = tid
        self.path = filePath
        self.needPost = needPost
        self.version = version
        self.isSuccess = isSuccess
        self.menuId = mid


class Processor(Module):

    def __init__(self, info:Info, cInst:Any) -> None:
        global M_NAME
        Module.__init__(self, M_NAME)

        self.__max = int(info.getConfig('MAX_TASK_CAN_PROC'))
        self.__numOfTasksInProc = 0
        self.__cInst = cInst
        self.__poolSize = int(info.getConfig('PROCESS_POOL_SIZE'))
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
        elif isinstance(reqLetter, PostTaskLetter):
            self.proc_post(reqLetter)

    @staticmethod
    def do_proc(reqLetter: NewLetter, info: Info) -> Result:
        isSuccess = True
        try:
            workerName = info.getConfig('WORKER_NAME')
            extra = reqLetter.getExtra()
            building_cmds = extra['cmds']
            result_path = extra['resultPath']
            needPost = reqLetter.needPost()
            menuId = reqLetter.getMenu()

            tid = reqLetter.getTid()

            if platform.system() == "Windows":
                result_path = result_path.replace("/", "\\")

        except:
            traceback.print_exc()

        # rocessing
        try:
            repo_url = info.getConfig("REPO_URL")
            projName = info.getConfig("PROJECT_NAME")

            # Get repo
            #os.system("git clone -b master " + repo_url)

            #os.chdir(projName)

            revision = reqLetter.getContent('sn')

            # Checkout to specific revision
            #os.system("git checkout -f " + revision)

            version = reqLetter.getContent('vsn')
            version_date = reqLetter.getContent('datetime')

            cmds_str =  ""
            if platform.system() == "Windows":
                cmds_str = "&&".join(building_cmds)
            else:
                cmds_str = ";".join(building_cmds)

            cmds_str = cmds_str.replace("<vsn>", version)
            cmds_str = cmds_str.replace("datetime>", version_date)

            # Run commands
            os.system(cmds_str)

        except Exception:
            traceback.print_exc()
            isSuccess = False

        return Result(tid, menuId, result_path, needPost, version, isSuccess)

    def proc_post(self, postTaskLetter:PostTaskLetter) -> State:
        listener = self.__cInst.getModule(POST_LISTENER_M_NAME) # type: PostListener

        # This worker is not a listener
        if listener is None:
            return Error

        listener.postAppend(postTaskLetter)

        return Ok

    def proc_command(self, cmdLetter:CommandLetter) -> State:

        type = cmdLetter.getHeader('type')
        subType = cmdLetter.getHeader('extra')

        if type not in cmdHandlers:
            return Error

        handler = cmdHandlers[type]

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

        # Resposne to configuration command
        server = cInst.getModule(SERVER_M_NAME)

        letter = CmdResponseLetter(cInst.getIdent(), CMD_POST_TYPE,
                                   CmdResponseLetter.STATE_SUCCESS,
                                   extra = {"isListener":"true"})
        server.transfer(letter)

        return Processor.__postProvider_config(address, port, info, cInst)

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

        # Response to configuraton command
        server = cInst.getModule(SERVER_M_NAME)

        letter = CmdResponseLetter(cInst.getIdent(), CMD_POST_TYPE, CmdResponseLetter.STATE_SUCCESS,
                                   extra={"isListener":"false"})
        server.transfer(letter)

        return Ok

    def proc_newtask(self, reqLetter:NewLetter) -> State:
        if not self.isAbleToProc():
            print("nable to proc")
            return Error

        tid = reqLetter.getHeader('tid')
        version = reqLetter.getContent('vsn')

        if self.isReqInProc(tid, version):
            print("In proc")
            return Error

        s = self.__cInst.getModule(SERVER_M_NAME)

        # Notify master this task is change into in_processing state
        response = ResponseLetter(ident=self.__cInst.getIdent(),
                                  tid=tid, state=Letter.RESPONSE_STATE_IN_PROC)
        s.transfer(response)

        res = self.__pool.apply_async(Processor.do_proc, (reqLetter, self.__info))
        self.__numOfTasksInProc += 1

        self.__allTasks.append((tid, version, res))
        self.__allTasks_dict[version+tid] = res

        return Ok

    # Remove tasks from processor and return
    # the number of request finished
    def recyle(self) -> int:
        (readies, not_readies) = partition(self.__allTasks, lambda res: res[2].ready())
        self.__allTasks = not_readies

        for (tid, version, res) in readies:
            result = res.get() # type: Result

            version = result.version
            tid = result.tid
            needPost = result.needPost
            path = result.path
            menu = result.menuId

            server = self.__cInst.getModule(SERVER_M_NAME)

            response = ResponseLetter(ident = self.__cInst.getIdent(), tid = tid,
                                      state = Letter.RESPONSE_STATE_FINISHED)

            if result.isSuccess is False:
                response.setState(Letter.RESPONSE_STATE_FAILURE)
                server.transfer(response)
                continue
            else:
                if needPost == "false":
                    self.__transBinaryTo(tid, path, lambda l: server.transfer(l))
                    server.transfer(response)
                else:
                    provider = self.__cInst.getModule(POST_PROVIDER_M_NAME) # type: PostProvider
                    self.__transBinaryTo(tid, path, lambda l: provider.provide(l), mid=menu,
                                         parent=version)
                    server.transfer(response)

            self.__numOfTasksInProc -= 1
            del self.__allTasks_dict [version+tid]

        return len(readies)

    def __transBinaryTo(self, tid:str, path:str,
                        transferRtn:Callable[[BinaryLetter], Any],
                        mid:str = "", parent:str = "") -> None:
        global sep

        fileName = path.split(sep)[-1]
        with open(path, "rb") as binFile:
            binLetter = BinaryLetter(tid=tid, bStr=b"", menu = mid,
                                     fileName=fileName, parent = parent)

            for line in binFile:
                binLetter.setBytes(line)
                transferRtn(binLetter)

            # Terminated binary letter
            binLetter.setBytes(b"")
            transferRtn(binLetter)

    def isReqInProc(self, tid:str, parent:str = "") -> bool:
        return tid in self.__allTasks_dict

    def isAbleToProc(self) -> bool:
        return self.tasksInProc() < self.maxTasksAbleToProc()


cmdHandlers = {
    CMD_POST_TYPE: Processor.post_config
} # type: Dict[str, CommandHandler]
