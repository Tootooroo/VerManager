# EventHandlers.py

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
    def do_action(self, t: Task, state: int) -> None:
        actions = self.ACTION_TBL[state]

        for action in actions:
            if action.isMatch(t):
                action.execute(t, action.args)

    @classmethod
    def install_action(self, state: int, action: ActionInfo) -> None:
        self.ACTION_TBL[state].append(action)

    @staticmethod
    def packDataWithChangeLog(vsn: str, filePath: str, dest: str,
                              log_start: str = "", log_end: str = "") -> str:

        from manager.models import infoBetweenRev

        changeLog = infoBetweenRev(log_start, log_end)

        with open("./log.txt", "w") as logFile:
            for log in changeLog:
                logFile.write(log)

        zipFileName = vsn + ".rar"

        zipFd = zipfile.ZipFile(dest + "/" + zipFileName, "w")
        for aFile in ["./log.txt", filePath]:
            zipFd.write(aFile)
        zipFd.close()

        return zipFileName

    @staticmethod
    def _singletask_fin_action(t: SingleTask,
                               eventListener: EventListener) -> None:

        if t.getParent() is None:
            responseHandler_ResultStore(t, eventListener)

    @staticmethod
    def _posttask_fin_action(t: PostTask,
                             eventListener: EventListener) -> None:
        super = t.getParent()
        assert(super is not None)

        extra = super.getExtra()
        assert(extra is not None)

        if "Temporary" in extra:
            temporaryBuild_handling(t, eventListener)
        else:
            responseHandler_ResultStore(super, eventListener)

        super.toFinState()

    @staticmethod
    def _tasks_fin_action(t: Task, eventListener: EventListener) -> None:
        taskId = t.id()
        chooserSet = EVENT_HANDLER_TOOLS.chooserSet
        if taskId in chooserSet:
            del chooserSet[taskId]

    @staticmethod
    def _tasks_fail_action(t: Task, eventListener: EventListener) -> None:

        if isinstance(t, SingleTask) or isinstance(t, PostTask):

            if t.isAChild():
                dispatcher = eventListener.getModule(DISPATCHER_M_NAME)
                assert(dispatcher is not None)

                parent = t.getParent()
                if isinstance(parent, SuperTask):
                    dispatcher.cancel(parent.id())


def responseHandler(eventListener: EventListener, letter: Letter) -> None:

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

    EVENT_HANDLER_TOOLS.do_action(task, state)

    if state == Task.STATE_FINISHED or state == Task.STATE_FAILURE:
        wr.removeTaskFromWorker(ident, taskId)


def temporaryBuild_handling(task: Task, eventListener:  EventListener) -> None:

    chooserSet = EVENT_HANDLER_TOOLS.chooserSet

    seperator = pathSeperator()

    taskId = task.id()

    chooser = chooserSet[taskId]
    filePath = chooser.path()
    fileName = filePath.split(seperator)[-1]

    if not os.path.exists("private"):
        os.mkdir("private")
    shutil.copy(filePath, "private" + seperator + fileName)


def responseHandler_ResultStore(task: Task,
                                eventListener:  EventListener) -> None:

    chooserSet = EVENT_HANDLER_TOOLS.chooserSet

    seperator = pathSeperator()

    # Pending feature
    # Store result to the target position specified in configuration file
    # Send email to notify that task id done
    try:

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

        if extra is not None and "logFrom" in extra and "logTo" in extra:
            fileName = EVENT_HANDLER_TOOLS.packDataWithChangeLog(
                fileName, chooser.path(), resultDir,
                extra['logFrom'],
                extra['logTo']
            )

        else:
            dest = resultDir + seperator + fileName
            shutil.copy(chooser.path(), dest)

        if not os.path.exists("public"):
            os.mkdir("public")
        shutil.copy(chooser.path(), "public/"+fileName)

    except FileNotFoundError:
        logger = eventListener.getModule('Logger')
        Logger.putLog(logger, letterLog, "ResultDir's value is invalid")

    url = cfgs.getConfig('GitlabUr')

    if not os.path.exists("./data"):
        os.mkdir("./data")

    task.setData(url + "/data/" + fileName)


def binaryHandler(eventListener:  EventListener, letter:  Letter) -> None:

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


def logHandler(eventListener: EventListener, letter: Letter) -> None:
    logger = eventListener.getModule(LOGGER_M_NAME)

    logId = letter.getHeader('logId')
    logMsg = letter.getContent('logMsg')

    if isinstance(logMsg, str):
        Logger.putLog(logger, logId, logMsg)


def logRegisterhandler(eventListener: EventListener, letter: Letter) -> None:
    logger = eventListener.getModule(LOGGER_M_NAME)

    logId = letter.getHeader('logId')
    logger.log_register(logId)


def postHandler(eventListener: EventListener, letter: Letter) -> None:

    if not isinstance(letter, CmdResponseLetter):
        return None

    wr = eventListener.getModule(WORKER_ROOM_MOD_NAME)  # type:  WorkerRoom
    wr.msgToPostManager(letter)


def lisAddrUpdateHandler(eventListener: EventListener, letter: Letter) -> None:
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

    addr, port = lis.getAddress()
    command = LisAddrUpdateCmd(addr, port)
    request_from = letter.getIdent()

    wr.control(request_from, command)
