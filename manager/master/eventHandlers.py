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

# EventHandlers.py

import asyncio
import concurrent.futures

import os
import zipfile
import shutil
import manager.master.configs as cfg

from typing import List, Dict, Optional, cast, Callable
from collections import namedtuple

from manager.master.eventListener \
    import letterLog, Entry

from manager.basic.type import Error
from manager.basic.letter import Letter, \
    ResponseLetter, BinaryLetter, NotifyLetter

from manager.master.task import Task, SuperTask, SingleTask, PostTask
from manager.master.dispatcher import Dispatcher

from manager.basic.storage import StoChooser

from manager.master.dispatcher import M_NAME as DISPATCHER_M_NAME
from manager.master.logger import Logger, M_NAME as LOGGER_M_NAME

from manager.master.workerRoom import WorkerRoom, M_NAME as WR_M_NAME

from manager.basic.info import M_NAME as INFO_M_NAME
from manager.basic.storage import M_NAME as STORAGE_M_NAME
from manager.basic.util import pathSeperator
from manager.basic.notify import Notify, WSCNotify

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
    def action_init(self, env: Entry.EntryEnv) -> None:
        # Fin action install
        singletask_fin_action_info = ActionInfo(
            isMatch=lambda t: isinstance(t, SingleTask),
            execute=self._singletask_fin_action,
            args=env
        )
        self.install_action(Task.STATE_FINISHED, singletask_fin_action_info)

        posttask_fin_action_info = ActionInfo(
            isMatch=lambda t: isinstance(t, PostTask),
            execute=self._posttask_fin_action,
            args=env
        )
        self.install_action(Task.STATE_FINISHED, posttask_fin_action_info)

        task_common_fin_action_info = ActionInfo(
            isMatch=lambda t: True,
            execute=self._tasks_fin_action,
            args=env
        )
        self.install_action(Task.STATE_FINISHED, task_common_fin_action_info)

        # Fail action install
        task_common_fail_action_info = ActionInfo(
            isMatch=lambda t: True,
            execute=self._tasks_fail_action,
            args=env
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
            t: SingleTask, env: Entry.EntryEnv) -> None:

        if t.getParent() is None:
            await responseHandler_ResultStore(t, env)

    @staticmethod
    async def _posttask_fin_action(t: PostTask, env: Entry.EntryEnv) -> None:
        super = t.getParent()
        assert(super is not None)

        extra = super.getExtra()
        assert(extra is not None)

        if "Temporary" in extra:
            await temporaryBuild_handling(t, env)
        else:
            await responseHandler_ResultStore(super, env)

        super.toFinState()

    @staticmethod
    async def _tasks_fin_action(t: Task, env: Entry.EntryEnv) -> None:
        taskId = t.id()
        chooserSet = EVENT_HANDLER_TOOLS.chooserSet
        if taskId in chooserSet:
            del chooserSet[taskId]

    @staticmethod
    async def _tasks_fail_action(t: Task, env: Entry.EntryEnv) -> None:

        if isinstance(t, SingleTask) or isinstance(t, PostTask):

            if t.isAChild():
                dispatcher = env.modules.getModule(DISPATCHER_M_NAME) \
                    # type: Dispatcher

                parent = t.getParent()
                if isinstance(parent, SuperTask):
                    await dispatcher.cancel(parent.id())


async def responseHandler(
        env: Entry.EntryEnv, letter: Letter) -> None:

    if not isinstance(letter, ResponseLetter):
        return None

    ident = letter.getHeader('ident')
    taskId = letter.getHeader('tid')
    state = int(letter.getContent('state'))

    wr = env.modules.getModule('WorkerRoom')  # type: WorkerRoom
    task = wr.getTaskOfWorker(ident, taskId)

    if task is None or not Task.isValidState(state):
        return None

    if task.stateChange(state) is Error:
        return None

    await EVENT_HANDLER_TOOLS.do_action(task, state)

    # Notify to components that
    # task's state is changed.
    type = env.eventListener.NOTIFY_TASK_STATE_CHANGED
    await env.eventListener.notify(type, (taskId, state))

    if state == Task.STATE_FINISHED or state == Task.STATE_FAILURE:
        wr.removeTaskFromWorker(ident, taskId)


async def copyFileInExecutor(src: str, dest: str) -> None:
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(EVENT_HANDLER_TOOLS.ProcessPool,
                               shutil.copy,
                               src, dest)


async def temporaryBuild_handling(
        task: Task, env: Entry.EntryEnv) -> None:

    logger = env.modules.getModule('Logger')

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


async def responseHandler_ResultStore(
        task: Task, env: Entry.EntryEnv) -> None:

    assert(cfg.config is not None)

    logger = env.modules.getModule('Logger')

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
    resultDir = cfg.config.getConfig("ResultDir")

    fileName = chooser.path().split(seperator)[-1]

    if not os.path.exists("./data"):
        os.mkdir("./data")
    if not os.path.exists("public"):
        os.mkdir("public")

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

        await copyFileInExecutor(chooser.path(), "public/"+fileName)

    except FileNotFoundError as e:
        await Logger.putLog(logger, letterLog, str(e))
    except PermissionError as e:
        await Logger.putLog(logger, letterLog, str(e))

    url = cfg.config.getConfig('GitlabUr')

    task.setData(url + "/data/" + fileName)


async def binaryHandler(env: Entry.EntryEnv, letter: Letter) -> None:

    """
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

            sto = env.modules.getModule(STORAGE_M_NAME)
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
    """
    return None


async def logHandler(env: Entry.EntryEnv, letter: Letter) -> None:
    logger = env.modules.getModule(LOGGER_M_NAME)

    logId = letter.getHeader('logId')
    logMsg = letter.getContent('logMsg')

    if isinstance(logMsg, str):
        await Logger.putLog(logger, logId, logMsg)


async def logRegisterhandler(env: Entry.EntryEnv, letter: Letter) -> None:
    logger = env.modules.getModule(LOGGER_M_NAME)
    logId = letter.getHeader('logId')
    logger.log_register(logId)


###############################################################################
#                               Notify Handlers                               #
###############################################################################
class NotifyHandleer:

    def __init__(self, env: Entry.EntryEnv) -> None:
        self._env = env

    async def handle(self, nl: NotifyLetter) -> None:
        handler = self._search_handler(nl)
        if handler is None:
            return None

    def _search_handler(self, nl: NotifyLetter) -> Optional[Callable[[NotifyLetter], None]]:
        type = nl.notifyType()
        try:
            return getattr(self, 'NOTIFY_H_'+type)
        except AttributeError:
            raise NOTIFY_NOT_MATCH_WITH_HANDLER(type)

    async def NOTIFY_H_WSC(self, nl: NotifyLetter) -> None:
        """
        Change state of correspond worker.
        """
        wsc_notify = cast(WSCNotify, Notify.transform(nl))
        who = wsc_notify.fromWho()
        state = wsc_notify.state()

        wr = self._env.modules.getModule(WR_M_NAME)  # type: WorkerRoom
        wr.setState(who, int(state))


class NOTIFY_NOT_MATCH_WITH_HANDLER(Exception):

    def __init__(self, type: str) -> None:
        self._type = type

    def __str__(self) -> str:
        return "Notify " + self._type + " not match with any handler"
