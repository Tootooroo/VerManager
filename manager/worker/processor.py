# processor.py

import time
import os
import traceback
import platform
import subprocess
import queue
import shutil

from typing import Any, Optional, Callable, List, Tuple, Dict
from multiprocessing import Pool, Manager
from multiprocessing.pool import AsyncResult
from threading import Event, Lock

from ..basic.letter import Letter, CommandLetter, NewLetter, PostTaskLetter, \
    LogLetter, LogRegLetter, CmdResponseLetter, ResponseLetter, BinaryLetter, \
    CancelLetter

from ..basic.storage import M_NAME as STO_M_NAME, Storage, File
from ..basic.observer import Subject
from ..basic.info import Info
from ..basic.type import Ok, Error, State
from ..basic.util import partition, excepHandle, pathSeperator, execute_shell, \
    packShellCommands

from ..basic.mmanager import Module

from .task import Task
from .post import Post
from .server import Server
from .postListener import PostListener, PostProvider

from ..basic.commands import Command, PostConfigCmd, LisAddrUpdateCmd, ReWorkCommand

from manager.worker.server import M_NAME as SERVER_M_NAME
from manager.worker.postListener import M_NAME as POST_LISTENER_M_NAME
from manager.worker.postListener import M_NAME_Provider as POST_PROVIDER_M_NAME
from manager.worker.sender import M_NAME as SENDER_M_NAME

from manager.basic.commands import CMD_POST_TYPE, CMD_ACCEPT, CMD_ACCEPT_RST, \
    CMD_LIS_ADDR_UPDATE, CMD_REWORK_TASK, CMD_CLEAN

Procedure = Callable[[Server, Post, Letter, Info], None]
CommandHandler = Callable[['Processor', CommandLetter, Info, Any], State]

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

class Processor(Module, Subject):

    def __init__(self, info:Info, cInst:Any) -> None:
        global M_NAME

        Module.__init__(self, M_NAME)
        Subject.__init__(self, M_NAME)

        self._max = int(info.getConfig('MAX_TASK_CAN_PROC'))
        self._numOfTasksInProc = 0
        self._cInst = cInst
        self._poolSize = int(info.getConfig('PROCESS_POOL_SIZE'))
        self._pool = Pool(self._poolSize)
        self._info = info

        self._procedure = None # type: Optional[Callable]

        # (tid, parent, result)
        self._allTasks = [] # type: List[Task]
        self._result_lock = Lock()

        # Query purpose
        self._allTasks_dict = {} # type: Dict[str, Task]

        self._manager = Manager()
        # Collections of event used to stop building processing.
        self._shell_events = {} # type: Dict[str, Event]

        self._recyleInterrupt = False
        self._recyleInProcessing = False

    def begin(self) -> None:
        return None

    def cleanup(self) -> None:
        return None

    def logging(self, msg:str) -> None:
        global LOG_ID

        if not hasattr(self, 'server'):
            self.server = self._cInst.getModule(SERVER_M_NAME)

            if self.server is None:
                return None

            regLetter = LogRegLetter(self._cInst.getIdent(), LOG_ID)
            self.server.transfer(regLetter)

        logLetter = LogLetter(self._cInst.getIdent(), LOG_ID, msg)
        self.server.transfer(logLetter)


    def maxTasksAbleToProc(self) -> int:
        return self._max

    def tasksInProc(self) -> int:
        return self._numOfTasksInProc

    def poolSize(self) -> int:
        return self._poolSize

    def setProcedure(self, procedure:Callable[[Server, Letter, Info], None]) -> None:
        self._procedure = procedure

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
            if ident in self._shell_events:
                self.stop_task(ident)
            else:
                return Error

        elif type == CancelLetter.TYPE_POST:
            post_listener = self._cInst.getModule(POST_LISTENER_M_NAME) \
                # type: Optional[PostListener]

            if post_listener is not None:
                post_listener.postRemove(ident)

        return Ok

    @staticmethod
    def do_proc(reqLetter: NewLetter, info: Info, stop:Event, path:str) -> Result:
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
                # Fetch from server
                "git fetch",
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

                if returncode != 0 and returncode != 128:
                    return result
                else:
                    break

            # Store generated file into Storage
            shutil.copy(projName + pathSeperator() + result_path, path)

        except Exception:
            traceback.print_exc()
            return result

        result.isSuccess = True
        return result

    def proc_post(self, postTaskLetter:PostTaskLetter) -> State:
        listener = self._cInst.getModule(POST_LISTENER_M_NAME) # type: PostListener

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

        return handler(self, cmdLetter, self._info, self._cInst)

    @staticmethod
    def command_clean(p:'Processor', cmdLetter:CommandLetter, info:Info, cInst:Any) -> State:
        pass

    @staticmethod
    def command_rework(p:'Processor', cmdLetter:CommandLetter, info:Info, cInst:Any) -> State:
        command = ReWorkCommand.fromLetter(cmdLetter)
        if command is None: return Error

        tid = command.tid()
        t = p.getTask(tid)

        # This task doesn't exists
        # which means the task is failure so
        # the task is removed.
        if t is None:
            return Error

        if t.state() >= Task.STATE_TRANSFER:

            result = t.result()
            if result.isSuccess is False:
                return Ok

            if t.state() == Task.STATE_TRANSFER:
                # Interrupt the in transfered task
                p.recyle_interrupt()

                # Wait task exit
                while p.isRecyleInProcessing(): time.sleep(0.01)

                # clean provider
                pr = cInst.getModule(POST_PROVIDER_M_NAME)
                if pr is None:
                    return Error
                else:
                    pr.removeAllStuffs()

                # Set task's state to In-Proc so it will be
                # dealt by Recyle()
                t.toProcState()

        return Ok

    @staticmethod
    def post_config(p:'Processor', cmdLetter:CommandLetter, info:Info, cInst:Any) -> State:

        cmd = PostConfigCmd.fromLetter(cmdLetter)

        if cmd is None:
            return Error

        (address, port) = cmd.address()

        role = cmd.role()

        if role is PostConfigCmd.ROLE_LISTENER:
            return Processor._postListener_config(p, address, port, info, cInst)
        elif role is PostConfigCmd.ROLE_PROVIDER:
            return Processor._postProvider_config(p, address, port, info, cInst)

        return Error

    @staticmethod
    def lisAddrUpdate(p: 'Processor', cmdLetter:CommandLetter,
                      info:Info, cInst:Any) -> State:

        cmd = LisAddrUpdateCmd.fromLetter(cmdLetter)
        if cmd is None:
            return Error

        address = cmd.address()

        # PostListener update
        if cInst.isModuleExists(POST_LISTENER_M_NAME):
            p.notify((0, address))

        # PostProvider update
        if cInst.isModuleExists(POST_PROVIDER_M_NAME):
            p.notify((1, address))

        return Ok

    @staticmethod
    def accepted_command(p: 'Processor', cmdLetter:CommandLetter,
                         info:Info, cInst:Any) -> State:
        """
        Worker has been accepted by master so worker is able to transfer messages
        to master.
        """
        server = cInst.getModule(SERVER_M_NAME)
        if server is None:
            return Error

        server.setStatus(Server.STATE_TRANSFER)
        return Ok

    @staticmethod
    def accepted_reset_command(p:'Processor', cmdLetter:CommandLetter,
                               info:Info, cInst:Any) -> State:
        """
        Worker should be reset itself before it transfer any data to master.
        """
        # Reset worker's status
        #
        # First cancel all tasks in processing
        global M_NAME

        p.stop_all_tasks()
        p.drop_all_results()
        p.recyle_interrupt()

        # Wait until recyle is stoped
        while p.isRecyleInProcessing():
            time.sleep(0.01)

        p.recyle_stop_interrupte()

        # Cleanup PostListener
        pl = cInst.getModule(POST_LISTENER_M_NAME)
        if pl is not None:
            pl.postRemoveAll()

        # Cleanup PostProvider
        pr = cInst.getModule(POST_PROVIDER_M_NAME)
        if pr is not None:
            pr.removeAllStuffs()

        # Cleanup Server
        server = cInst.getModule(SERVER_M_NAME)
        server.drop_all_messages()

        # Set to accept state
        return Processor.accepted_command(p, cmdLetter, info, cInst)

    @staticmethod
    def _postListener_config(p:'Processor', address:str,
                              port:int, info:Info, cInst:Any) -> State:

        if not cInst.isModuleExists(POST_LISTENER_M_NAME):
            pl = PostListener(address, port, cInst)
            pl.start()

            p.subscribe(pl)
            pl.handler_install(M_NAME, pl.address_update)

            cInst.addModule(pl)
        else:
            """
            A PostListener is already exists on this worker
            so need to create a new one. But the address
            used by the listener may out of date. Need
            to notify a new address to the PostListener.
            """
            p.notify((0, address))

        # Resposne to configuration command
        server = cInst.getModule(SERVER_M_NAME)

        letter = CmdResponseLetter(cInst.getIdent(), CMD_POST_TYPE,
                                   CmdResponseLetter.STATE_SUCCESS,
                                   extra = {"isListener":"true"})
        server.transfer(letter)
        return Ok

    @staticmethod
    def _postProvider_config(p:'Processor', address:str, port:int, info:Info, cInst:Any) -> State:

        sender = cInst.getModule(SENDER_M_NAME)
        if cInst.isModuleExists(POST_PROVIDER_M_NAME):
            p.notify((1, address))
        else:
            provider = PostProvider(address, port, cInst)

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

            sender.rtnRegister(provider.provide_step)

            p.subscribe(provider)
            provider.handler_install(M_NAME, provider.address_update)

            cInst.addModule(provider)

        # Response to configuraton command
        server = cInst.getModule(SERVER_M_NAME)
        letter = CmdResponseLetter(cInst.getIdent(), CMD_POST_TYPE,
                                   CmdResponseLetter.STATE_SUCCESS,
                                   extra={"isListener":"false"})
        server.transfer(letter)
        return Ok

    def stop_task(self, taskId:str) -> None:
        if taskId in self._shell_events:
            self._shell_events[taskId].set()

    def stop_all_tasks(self) -> None:
        for taskId in self._shell_events:
            self._shell_events[taskId].set()

    def drop_all_results(self) -> None:
        with self._result_lock:
            self._allTasks = []
            self._allTasks_dict = {}

    def recyle_lock(self) -> None:
        self._result_lock.acquire()

    def recyle_unlock(self) -> None:
        self._result_lock.release()

    def recyle_interrupt(self) -> None:
        self._recyleInterrupt = True

    def recyle_stop_interrupte(self) -> None:
        self._recyleInterrupt = False

    def proc_newtask(self, reqLetter:NewLetter) -> State:
        if not self.isAbleToProc():
            return Error

        tid = reqLetter.getHeader('tid')
        if tid in self._shell_events:
            return Error

        version = reqLetter.getContent('vsn')

        if self.isReqInProc(tid, version):
            return Error

        s = self._cInst.getModule(SERVER_M_NAME)

        # Notify master this task is change into in_processing state
        response = ResponseLetter(ident=self._cInst.getIdent(),
                                tid=tid, state=Letter.RESPONSE_STATE_IN_PROC)
        s.transfer(response)

        event = self._manager.Event()
        self._shell_events[tid] = event

        # Create a file in storage this file will be
        # overwrite by generated file if task successed.
        storage = self._cInst.getModule(STO_M_NAME)
        assert(storage is not None)

        resultPath = reqLetter.getExtra()['resultPath']
        fileName = resultPath.split(pathSeperator())[-1]
        sto = storage.create(version, fileName)

        res = self._pool.apply_async(
            Processor.do_proc, (reqLetter, self._info, event, sto._path)
        )

        filePath = reqLetter.getExtra()['resultPath']
        t = Task(tid, version, res, filePath)

        # Changed task's state to Proc so it can be dealt by
        # recyle() onece it's ready.
        t.toProcState()

        self.addTask(t)

        return Ok

    # Remove tasks from processor and return
    # the number of request finished
    def recyle(self) -> int:

        self._recyleInProcessing = True

        filter_f = lambda t: t.isReady() and (t.state() == Task.STATE_PROC or
                                       t.state() == Task.STATE_TRANSFER)

        with self._result_lock:
            (readies, not_readies) = partition(self._allTasks, filter_f)

        for t in readies:

            if self._recyleInterrupt:
                break

            t.toTransferState()

            tid = t.tid()
            version = t.version()

            if tid in self._shell_events:
                del self._shell_events [tid]

            result = t.result() # type: Result
            version = result.version
            tid = result.tid
            needPost = result.needPost

            # Build path to result
            fileName = result.path.split(pathSeperator())[-1]

            storage = self._cInst.getModule(STO_M_NAME)
            assert(storage is not None)

            file = storage.getFile(version, fileName)

            # Task is already be cleaned.
            if file is None:
                self.removeTask(tid)
                continue

            path = file.path()

            menu = result.menuId

            server = self._cInst.getModule(SERVER_M_NAME)
            provider = self._cInst.getModule(POST_PROVIDER_M_NAME)

            response = ResponseLetter(ident = self._cInst.getIdent(), tid = tid,
                                      state = Letter.RESPONSE_STATE_FINISHED)

            # Task is failure clean the task
            if result.isSuccess is False:
                # Tell to master this task is failed.
                response.setState(Letter.RESPONSE_STATE_FAILURE)
                server.transfer(response)
                t.toDoneState()

                # Delete file correspond to this task
                storage = self._cInst.getModule(STO_M_NAME)
                assert(storage is not None)
                storage.delete(version, path.split(pathSeperator())[-1])

                # Remove the task from Processor
                self.removeTask(t.tid())

            else:
                # Transfer Binary
                if needPost == "false":
                    # Tasks that no post can not be interrupted.
                    if self._transBinaryTo(tid, path, lambda l: server.transfer(l)) == 0:
                        server.transfer(response)
                        t.toDoneState()
                    else:
                        break

                else:
                    if provider is None:
                        response.setState(Letter.RESPONSE_STATE_FAILURE)
                        server.transfer(response)
                    else:
                        try:
                            # Transfer generated file to PostListener or master
                            ret = self._transBinaryTo(tid, path,
                                                      lambda l: provider.provide(l, 10),
                                                      mid=menu,
                                                      parent=version)

                            # Transfer done
                            if ret == 0:
                                # Notify to master
                                server.transfer(response)
                                t.toDoneState()
                            else:
                                # Transfer is interrupted
                                break

                        except BinaryLetter.FIELD_LENGTH_EXCEPTION:
                            response.setState(Letter.RESPONSE_STATE_FAILURE)
                        except FileNotFoundError:
                            response.setState(Letter.RESPONSE_STATE_FAILURE)
                        except queue.Full:
                            response.setState(Letter.RESPONSE_STATE_FAILURE)

        self._recyleInProcessing = False

        return len(readies)

    # 0: Normal
    # 1: Be interrupted
    def _transBinaryTo(self, tid:str, path:str,
                       transferRtn:Callable[[BinaryLetter], Any],
                       mid:str = "", parent:str = "") -> int:

        seperator = pathSeperator()

        with open(path, "rb") as binFile:
            fileName = path.split(seperator)[-1]

            for line in binFile:

                if self._recyleInterrupt:
                    return 1

                binLetter = BinaryLetter(tid=tid, bStr=line, menu=mid,
                                         fileName=fileName, parent=parent)
                transferRtn(binLetter)

        # Terminated binary letter
        binLetter_last = BinaryLetter(tid=tid, bStr=b"", menu = mid,
                                    fileName=fileName, parent = parent)
        transferRtn(binLetter_last)

        return 0

    def isRecyleInProcessing(self) -> bool:
        return self._recyleInProcessing

    def isReqInProc(self, tid:str, parent:str = "") -> bool:
        return tid in self._allTasks_dict

    def isAbleToProc(self) -> bool:
        return self.tasksInProc() < self.maxTasksAbleToProc()

    def getTask(self, tid) -> Optional[Task]:
        if tid in self._allTasks_dict:
            return self._allTasks_dict[tid]
        return None

    def addTask(self, t:Task) -> None:
        tid = t.tid()

        if tid in self._allTasks_dict:
            return None

        self._allTasks_dict[tid] = t
        self._allTasks.append(t)

        self._numOfTasksInProc += 1

    def removeTask(self, tid:str) -> None:

        if tid not in self._allTasks_dict:
            return None

        del self._allTasks_dict [tid]
        self._allTasks = [t for t in self._allTasks if t.tid() != tid]

        self._numOfTasksInProc -= 1



cmdHandlers = {
    CMD_POST_TYPE:       Processor.post_config,
    CMD_ACCEPT:          Processor.accepted_command,
    CMD_ACCEPT_RST:      Processor.accepted_reset_command,
    CMD_LIS_ADDR_UPDATE: Processor.lisAddrUpdate,
    CMD_REWORK_TASK:     Processor.command_rework,
    CMD_CLEAN:           Processor.command_clean
} # type: Dict[str, CommandHandler]
