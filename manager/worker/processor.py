# processor.py

import time
import os
import traceback
import platform
import subprocess
import queue

from typing import Any, Optional, Callable, List, Tuple, Dict
from multiprocessing import Pool, Manager
from multiprocessing.pool import AsyncResult
from threading import Event

from ..basic.letter import Letter, CommandLetter, NewLetter, PostTaskLetter, \
    LogLetter, LogRegLetter, CmdResponseLetter, ResponseLetter, BinaryLetter, \
    CancelLetter

from ..basic.info import Info
from ..basic.type import Ok, Error, State
from ..basic.util import partition, excepHandle, pathSeperator, execute_shell, \
    packShellCommands

from ..basic.mmanager import Module

from .post import Post
from .server import Server
from .postListener import PostListener, PostProvider

from ..basic.commands import Command, PostConfigCmd, CMD_POST_TYPE

from manager.worker.server import M_NAME as SERVER_M_NAME
from manager.worker.postListener import M_NAME as POST_LISTENER_M_NAME
from manager.worker.postListener import M_NAME_Provider as POST_PROVIDER_M_NAME
from manager.worker.sender import M_NAME as SENDER_M_NAME

from manager.basic.commands import CMD_POST_TYPE

Procedure = Callable[[Server, Post, Letter, Info], None]
CommandHandler = Callable[[CommandLetter, Info, Any], State]

M_NAME = "Processor"
LOG_ID = "Processor"

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

        self.__manager = Manager()
        # Collections of event used to stop building processing.
        self.__shell_events = {} # type: Dict[str, Event]

    def logging(self, msg:str) -> None:
        global LOG_ID

        if not hasattr(self, 'server'):
            self.server = self.__cInst.getModule(SERVER_M_NAME)

            if self.server is None:
                return None

            regLetter = LogRegLetter(self.__cInst.getIdent(), LOG_ID)
            self.server.transfer(regLetter)

        logLetter = LogLetter(self.__cInst.getIdent(), LOG_ID, msg)
        self.server.transfer(logLetter)


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
        elif isinstance(reqLetter, CancelLetter):
            self.proc_cancel(reqLetter)

    def proc_cancel(self, letter:CancelLetter) -> State:
        ident = letter.getIdent()
        type = letter.getType()

        if type == CancelLetter.TYPE_SINGLE:
            if ident in self.__shell_events:
                self.sotp_task(ident)
            else:
                return Error

        elif type == CancelLetter.TYPE_POST:
            post_listener = self.__cInst.getModule(POST_LISTENER_M_NAME) \
                # type: Optional[PostListener]

            if post_listener is not None:
                post_listener.postRemove(ident)

        return Ok

    @staticmethod
    def do_proc(reqLetter: NewLetter, info: Info, stop:Event) -> Result:
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
            revision = reqLetter.getContent('sn')
            version = reqLetter.getContent('vsn')
            version_date = reqLetter.getContent('datetime')

            result = Result(tid, menuId, result_path, needPost, version, False)

            commands = [
                # Go into project root
                "cd " + projName,
                # Checkout the version
                "git checkout -f " + revision
            ] + building_cmds

            if not os.path.exists(projName):
                commands = ["git clone -b master " + repo_url] + commands

            # Pack all building commands into a single string
            # so all of them will be executed in the same shell
            # environment.
            cmds_str = packShellCommands(commands)

            # Run building commands
            handle = execute_shell(cmds_str)
            if handle is None:
                return result

            while True:
                try:
                    if stop.is_set():
                        handle.terminate()
                        return result

                    returncode = handle.wait(1)
                except subprocess.TimeoutExpired:
                    continue

                if returncode is not 0 and returncode is not 128:
                    return result
                else:
                    break

        except Exception:
            traceback.print_exc()
            return result

        result.isSuccess = True
        return result

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

        if cInst.isModuleExists(POST_LISTENER_M_NAME):
            cInst.removeModule(POST_LISTENER_M_NAME)

        pl = PostListener(address, port, cInst)
        pl.start()

        cInst.addModule(pl)

        # Resposne to configuration command
        server = cInst.getModule(SERVER_M_NAME)

        letter = CmdResponseLetter(cInst.getIdent(), CMD_POST_TYPE,
                                   CmdResponseLetter.STATE_SUCCESS,
                                   extra = {"isListener":"true"})
        server.transfer(letter)
        return Ok

    @staticmethod
    def __postProvider_config(address:str, port:int, info:Info, cInst:Any) -> State:

        if cInst.isModuleExists(POST_PROVIDER_M_NAME):
            cInst.removeModule(POST_PROVIDER_M_NAME)

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

        sender = cInst.getModule(SENDER_M_NAME)
        sender.rtnRegister(lambda : provider.provide_step())

        cInst.addModule(provider)

        # Response to configuraton command
        server = cInst.getModule(SERVER_M_NAME)
        letter = CmdResponseLetter(cInst.getIdent(), CMD_POST_TYPE,
                                   CmdResponseLetter.STATE_SUCCESS,
                                   extra={"isListener":"false"})
        server.transfer(letter)

        return Ok

    def sotp_task(self, taskId:str) -> None:
        if taskId in self.__shell_events:
            self.__shell_events[taskId].set()

    def proc_newtask(self, reqLetter:NewLetter) -> State:
        if not self.isAbleToProc():
            return Error

        tid = reqLetter.getHeader('tid')
        if tid in self.__shell_events:
            return Error

        version = reqLetter.getContent('vsn')

        if self.isReqInProc(tid, version):
            return Error

        s = self.__cInst.getModule(SERVER_M_NAME)

        # Notify master this task is change into in_processing state
        response = ResponseLetter(ident=self.__cInst.getIdent(),
                                tid=tid, state=Letter.RESPONSE_STATE_IN_PROC)
        s.transfer(response)

        event = self.__manager.Event()
        self.__shell_events[tid] = event

        res = self.__pool.apply_async(Processor.do_proc,
                                    (reqLetter, self.__info, event))

        self.__allTasks.append((tid, version, res))
        self.__allTasks_dict[version+tid] = res

        return Ok

    # Remove tasks from processor and return
    # the number of request finished
    def recyle(self) -> int:
        (readies, not_readies) = partition(self.__allTasks, lambda res: res[2].ready())
        self.__allTasks = not_readies

        for (tid, version, res) in readies:

            if tid in self.__shell_events:
                del self.__shell_events [tid]

            result = res.get() # type: Result

            version = result.version
            tid = result.tid
            needPost = result.needPost

            # Build path to result
            projName = self.__info.getConfig("PROJECT_NAME")
            path = projName + pathSeperator() + result.path

            menu = result.menuId

            server = self.__cInst.getModule(SERVER_M_NAME)
            provider = self.__cInst.getModule(POST_PROVIDER_M_NAME)

            response = ResponseLetter(ident = self.__cInst.getIdent(), tid = tid,
                                      state = Letter.RESPONSE_STATE_FINISHED)

            if result.isSuccess is False:
                # Tell to master this task is failed.
                response.setState(Letter.RESPONSE_STATE_FAILURE)
                server.transfer(response)

            else:
                # Transfer Binary
                if needPost == "false":
                    self.__transBinaryTo(tid, path, lambda l: server.transfer(l))
                else:
                    if provider is None:
                        response.setState(Letter.RESPONSE_STATE_FAILURE)
                        server.transfer(response)
                    else:
                        try:
                            self.__transBinaryTo(tid, path,
                                            lambda l: provider.provide(l, 10),
                                            mid=menu,
                                            parent=version)
                        except BinaryLetter.FIELD_LENGTH_EXCEPTION:
                            response.setState(Letter.RESPONSE_STATE_FAILURE)
                        except FileNotFoundError:
                            response.setState(Letter.RESPONSE_STATE_FAILURE)
                        except queue.Full:
                            response.setState(Letter.RESPONSE_STATE_FAILURE)

                # Notify to master
                server.transfer(response)

            self.__numOfTasksInProc -= 1
            del self.__allTasks_dict [version+tid]

        return len(readies)

    def __transBinaryTo(self, tid:str, path:str,
                        transferRtn:Callable[[BinaryLetter], Any],
                        mid:str = "", parent:str = "") -> None:

        seperator = pathSeperator()

        with open(path, "rb") as binFile:
            fileName = path.split(seperator)[-1]
            for line in binFile:
                binLetter = BinaryLetter(tid=tid, bStr=line, menu=mid,
                                         fileName=fileName, parent=parent)
                transferRtn(binLetter)

        # Terminated binary letter
        binLetter_last = BinaryLetter(tid=tid, bStr=b"", menu = mid,
                                    fileName=fileName, parent = parent)
        transferRtn(binLetter_last)

    def isReqInProc(self, tid:str, parent:str = "") -> bool:
        return tid in self.__allTasks_dict

    def isAbleToProc(self) -> bool:
        return self.tasksInProc() < self.maxTasksAbleToProc()


cmdHandlers = {
    CMD_POST_TYPE: Processor.post_config
} # type: Dict[str, CommandHandler]
