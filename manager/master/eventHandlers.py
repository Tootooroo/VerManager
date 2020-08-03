# EventHandlers.py

import asyncio
import concurrent.futures

import os
import zipfile
import shutil

from typing import List, Dict, Optional
from collections import namedtuple

from manager.master.eventListener import EventListener, letterLog

from manager.basic.type import Error
from manager.basic.letter import Letter, \
    CmdResponseLetter, ResponseLetter, BinaryLetter, ReqLetter

from manager.master.task import Task, SuperTask, SingleTask, PostTask
from manager.master.dispatcher import Dispatcher

from manager.basic.commands import LisAddrUpdateCmd
from manager.basic.storage import StoChooser

from manager.master.dispatcher import M_NAME as DISPATCHER_M_NAME
from manager.master.logger import Logger, M_NAME as LOGGER_M_NAME

from manager.master.workerRoom import WorkerRoom
from manager.master.workerRoom import M_NAME as WORKER_ROOM_MOD_NAME

from manager.basic.info import M_NAME as INFO_M_NAME
from manager.basic.storage import M_NAME as STORAGE_M_NAME
from manager.basic.util import pathSeperator

ActionInfo = namedtuple('ActionInfo', 'isMatch execute args')


class EVENT_HANDLER_TOOLS:

    ProcessPool = concurrent.futures.ProcessPoolExecutor()
    chooserSet = {}  # type: Dict[str, StoChooser]

    PREPARE_ACTIONS = []  # type: List[ActionInfo]
    IN_PROC_ACTIONS = []  # type: List[ActionInfo]
    FIN_ACTIONS = []   # type: List[ActionInfo]
    FAIL_ACTIONS = []   # type: List[ActionInfo]

    ACTION_TBL = {
        Task.STATE_IN_PROC: IN_PROC_ACTIONS,
        Task.STATE_FINISHED: FIN_ACTIONS,
        Task.STATE_FAILURE: FAIL_ACTIONS
    }  # type: Dict[int, List[ActionInfo]]

    @classmethod
    def action_init(self, eventListener: EventListener) -> None:
        # Fin action install
        singletask_fin_action_info = ActionInfo(
            isMatch=lambda t: isinstance(t, SingleTask),
            execute=self._singletask_fin_action,
            args=eventListener
        )
        self.install_action(Task.STATE_FINISHED, singletask_fin_action_info)

        posttask_fin_action_info = ActionInfo(
            isMatch=lambda t: isinstance(t, PostTask),
            execute=self._posttask_fin_action,
            args=eventListener
        )
        self.install_action(Task.STATE_FINISHED, posttask_fin_action_info)

        task_common_fin_action_info = ActionInfo(
            isMatch=lambda t: True,
            execute=self._tasks_fin_action,
            args=eventListener
        )
        self.install_action(Task.STATE_FINISHED, task_common_fin_action_info)

        # Fail action install
        task_common_fail_action_info = ActionInfo(
            isMatch=lambda t: True,
            execute=self._tasks_fail_action,
            args=eventListener
        )
        self.install_action(Task.STATE_FAILURE, task_common_fail_action_info)

    @classmethod
    async def do_action(self, t: Task, state: int) -> None:
        actions = self.ACTION_TBL[state]

        for action in actions:
            if action.isMatch(t):
                await action.execute(t, action.args)

    @classmethod
    def install_action(self, state: int, action: ActionInfo) -> None:
        self.ACTION_TBL[state].append(action)

    @classmethod
    async def packDataWithChangeLog(self, vsn: str, filePath: str, dest: str,
                                    log_start: str = "",
                                    log_end: str = "") -> str:

        zipFileName = vsn + ".rar"
        zipPath = dest + "/" + zipFileName
        self.changeLogGen(log_start, log_end, "./log.txt")

        # Pack into a zipfile may take a while
        # do it in another process.
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            EVENT_HANDLER_TOOLS.ProcessPool,
            self.zipPackHelper,
            ["./log.txt", filePath], zipPath
        )

        return zipFileName

    @staticmethod
    def changeLogGen(start_commit: str,
                     last_commit: str,
                     destPath: str) -> None:

        from manager.models import infoBetweenRev
        changeLog = infoBetweenRev(start_commit, last_commit)

        with open(destPath, "w") as logFile:
            for log in changeLog:
                logFile.write(log)

    @staticmethod
    def zipPackHelper(files: List[str], zipPath: str) -> None:
        zipFd = zipfile.ZipFile(zipPath)
        for f in files:
            zipFd.write(f)
        zipFd.close()

    @staticmethod
    async def _singletask_fin_action(
            t: SingleTask, eventListener: EventListener) -> None:

        if t.getParent() is None:
            await responseHandler_ResultStore(t, eventListener)

    @staticmethod
    async def _posttask_fin_action(t: PostTask,
                                   eventListener: EventListener) -> None:
        super = t.getParent()
        assert(super is not None)

        extra = super.getExtra()
        assert(extra is not None)

        if "Temporary" in extra:
            await temporaryBuild_handling(t, eventListener)
        else:
            await responseHandler_ResultStore(super, eventListener)

        super.toFinState()

    @staticmethod
    async def _tasks_fin_action(t: Task, eventListener: EventListener) -> None:
        taskId = t.id()
        chooserSet = EVENT_HANDLER_TOOLS.chooserSet
        if taskId in chooserSet:
            del chooserSet[taskId]

    @staticmethod
    async def _tasks_fail_action(t: Task,
                                 eventListener: EventListener) -> None:

        if isinstance(t, SingleTask) or isinstance(t, PostTask):

            if t.isAChild():
                dispatcher = eventListener.getModule(DISPATCHER_M_NAME)  \
                    # type: Dispatcher

                assert(dispatcher is not None)

                parent = t.getParent()
                if isinstance(parent, SuperTask):
                    await dispatcher.cancel(parent.id())


async def responseHandler(eventListener: EventListener,
                          letter: Letter) -> None:

    if not isinstance(letter, ResponseLetter):
        return None

    ident = letter.getHeader('ident')
    taskId = letter.getHeader('tid')
    state = int(letter.getContent('state'))

    wr = eventListener.getModule('WorkerRoom') \
        # type: Optional[WorkerRoom]
    assert(wr is not None)

    task = wr.getTaskOfWorker(ident, taskId)

    if task is None or not Task.isValidState(state):
        return None

    if task.stateChange(state) is Error:
        return None

    await EVENT_HANDLER_TOOLS.do_action(task, state)

    if state == Task.STATE_FINISHED or state == Task.STATE_FAILURE:
        wr.removeTaskFromWorker(ident, taskId)


async def copyFileInExecutor(src: str, dest: str) -> None:
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(EVENT_HANDLER_TOOLS.ProcessPool,
                               shutil.copy,
                               src, dest)


async def temporaryBuild_handling(task: Task,
                                  eventListener:  EventListener) -> None:

    logger = eventListener.getModule('Logger')

    chooserSet = EVENT_HANDLER_TOOLS.chooserSet
    seperator = pathSeperator()
    taskId = task.id()

    chooser = chooserSet[taskId]
    filePath = chooser.path()
    fileName = filePath.split(seperator)[-1]

    try:
        if not os.path.exists("private"):
            os.mkdir("private")

        # Copy may happen on NFS may take a long time to deal
        # just run in another process.
        await copyFileInExecutor(filePath, "private" + seperator + fileName)

    except FileNotFoundError as e:
        Logger.putLog(logger, letterLog, str(e))
    except PermissionError as e:
        Logger.putLog(logger, letterLog, str(e))


async def responseHandler_ResultStore(task: Task,
                                      eventListener:  EventListener) -> None:

    logger = eventListener.getModule('Logger')

    chooserSet = EVENT_HANDLER_TOOLS.chooserSet
    seperator = pathSeperator()

    # Pending feature
    # Store result to the target position specified in configuration file
    # Send email to notify that task id done
    if isinstance(task, SuperTask):
        # Binary file correspond to a SuperTask
        # is transfer from PostListener.
        taskId = PostTask.genIdent(task.id())
    else:
        taskId = task.id()

    extra = task.getExtra()
    chooser = chooserSet[taskId]

    cfgs = eventListener.getModule(INFO_M_NAME)
    resultDir = cfgs.getConfig("ResultDir")

    fileName = chooser.path().split(seperator)[-1]

    try:
        if extra is not None and "logFrom" in extra and "logTo" in extra:
            fileName = await EVENT_HANDLER_TOOLS.packDataWithChangeLog(
                fileName, chooser.path(), resultDir,
                extra['logFrom'],
                extra['logTo']
            )
        else:
            dest = resultDir + seperator + fileName
            shutil.copy(chooser.path(), dest)

        if not os.path.exists("public"):
            os.mkdir("public")
        await copyFileInExecutor(chooser.path(), "public/"+fileName)

    except FileNotFoundError as e:
        Logger.putLog(logger, letterLog, str(e))
    except PermissionError as e:
        Logger.putLog(logger, letterLog, str(e))

    url = cfgs.getConfig('GitlabUr')

    if not os.path.exists("./data"):
        os.mkdir("./data")

    task.setData(url + "/data/" + fileName)


async def binaryHandler(eventListener: EventListener, letter: Letter) -> None:

    import traceback

    chooserSet = EVENT_HANDLER_TOOLS.chooserSet

    if not isinstance(letter, BinaryLetter):
        return None

    try:
        tid = letter.getHeader('tid')

        # This is the first binary letter of the task correspond to the
        # received tid just open a file and store the relation into fdSet
        if tid not in chooserSet:
            fileName = letter.getFileName()
            version = letter.getParent()

            sto = eventListener.getModule(STORAGE_M_NAME)
            chooser = sto.create(version, fileName)
            chooserSet[tid] = chooser

        chooser = chooserSet[tid]
        content = letter.getContent('bytes')

        if isinstance(content, str):
            return None

        if content == b"":
            chooser.close()
        else:
            chooser.store(content)
    except Exception:
        traceback.print_exc()


async def logHandler(eventListener: EventListener, letter: Letter) -> None:
    logger = eventListener.getModule(LOGGER_M_NAME)

    logId = letter.getHeader('logId')
    logMsg = letter.getContent('logMsg')

    if isinstance(logMsg, str):
        await Logger.putLog(logger, logId, logMsg)


async def logRegisterhandler(eventListener: EventListener,
                             letter: Letter) -> None:

    logger = eventListener.getModule(LOGGER_M_NAME)

    logId = letter.getHeader('logId')
    logger.log_register(logId)


async def postHandler(eventListener: EventListener, letter: Letter) -> None:
    if not isinstance(letter, CmdResponseLetter):
        return None

    wr = eventListener.getModule(WORKER_ROOM_MOD_NAME)  # type:  WorkerRoom
    await wr.msgToPostManager(letter)


async def lisAddrUpdateHandler(eventListener: EventListener,
                               letter: Letter) -> None:
    """
    This handler does not to ensure that that last address
    is successfully sended to worker.

    This Handler may return before send command due to:
    (1) There is no listener may cause of the election is in processed.
    (2) Requested worker is lost after it sended this request
    """
    if not isinstance(letter, ReqLetter):
        return None

    wr = eventListener.getModule(WORKER_ROOM_MOD_NAME)  \
        # type:  Optional[WorkerRoom]

    if wr is None:
        return None

    # Get listener's address.
    lis = wr.postListener()
    if lis is None:
        return None

    addr = lis.getAddress()
    command = LisAddrUpdateCmd(addr)
    request_from = letter.getIdent()

    await wr.control(request_from, command)
