# EventHandlers.py

import zipfile
import shutil

from manager.master.eventListener import EventListener, letterLog

from manager.basic.type import Ok, Error, State
from manager.basic.letter import *
from manager.master.task import Task, SuperTask, SingleTask, PostTask

from manager.basic.commands import PostConfigCmd, LisAddrUpdateCmd
from manager.basic.storage import Storage, StoChooser

from manager.master.dispatcher import M_NAME as DISPATCHER_M_NAME, Dispatcher
from manager.master.logger import Logger, M_NAME as LOGGER_M_NAME

from manager.master.workerRoom import WorkerRoom
from manager.master.workerRoom import M_NAME as WORKER_ROOM_MOD_NAME
from manager.master.postElection import PostManager, Role_Listener

from manager.master.worker import Worker

from manager.basic.info import Info, M_NAME as INFO_M_NAME
from manager.basic.storage import M_NAME as STORAGE_M_NAME
from manager.basic.util import pathSeperator

def packDataWithChangeLog(vsn: str, filePath: str, dest: str, log_start:str = "", log_end:str = "") -> str:
    from manager.models import infoBetweenRev, Versions

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

chooserSet = {} # type: Dict[str, StoChooser]

def responseHandler(eventListener:EventListener, letter:Letter) -> None:

    global chooserSet

    if letter.typeOfLetter() != Letter.Response:
        return None

    ident = letter.getHeader('ident')
    taskId = letter.getHeader('tid')
    state = int(letter.getContent('state'))

    workers = eventListener.getModule('WorkerRoom') # type: Optional[WorkerRoom]
    assert(workers is not None)

    worker = workers.getWorker(ident)

    if worker is None:
        return None

    task = worker.searchTask(taskId)

    if task is not None and Task.isValidState(state):

        ret = task.stateChange(state)
        # Invalid state shift.
        if ret is Error:
            return None

        if state == Task.STATE_FINISHED:

            if isinstance(task, SingleTask):
                if task.getParent() is None:
                    responseHandler_ResultStore(eventListener, task)

            elif isinstance(task, PostTask):
                super = task.getParent()
                assert(super is not None)

                extra = super.getExtra()
                assert(extra is not None)

                if "Temporary" in extra:
                    temporaryBuild_handling(eventListener, task)
                else:
                    responseHandler_ResultStore(eventListener, super)

                super.toFinState()

            print("Remove Task: " + taskId)
            worker.removeTask(taskId)

            # Close chooser
            if taskId in chooserSet:
                chooser = chooserSet[taskId]
                del chooserSet [taskId]

        elif state == Task.STATE_FAILURE:

            # If this task is a member of SuperTask
            # then we need to cancel all tasks that
            # belong to the SuperTask
            if isinstance(task, SingleTask) or isinstance(task, PostTask):

                if task.isAChild():
                    dispatcher = eventListener.getModule(DISPATCHER_M_NAME) \
                        # type: Dispatcher

                    parent = task.getParent()
                    if parent is not None:
                        dispatcher.cancel(parent.id())

            # Remove Task from worker
            worker.removeTask(taskId)

def temporaryBuild_handling(eventListener: EventListener, task: Task) -> None:
    global chooserSet
    seperator = pathSeperator()

    taskId = task.id()

    chooser = chooserSet[taskId]
    filePath = chooser.path()
    fileName = filePath.split(seperator)[-1]

    shutil.copy(filePath, "private" + seperator + fileName)


def responseHandler_ResultStore(eventListener: EventListener,
                                task: Task) -> None:

    global chooserSet

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

        version = task.getVSN()
        extra = task.getExtra()
        chooser = chooserSet[taskId]

        cfgs = eventListener.getModule(INFO_M_NAME)
        resultDir = cfgs.getConfig("ResultDir")

        fileName = chooser.path().split(seperator)[-1]

        if extra is not None and "logFrom" in extra and "logTo" in extra:
            fileName = packDataWithChangeLog(fileName,
                                             chooser.path(), resultDir,
                                             extra['logFrom'], extra['logTo'])
        else:
            dest = resultDir + seperator + fileName
            shutil.copy(chooser.path(), dest)

        shutil.copy(chooser.path(), "public/"+fileName)

    except FileNotFoundError:
        logger = eventListener.getModule('Logger')
        Logger.putLog(logger, letterLog, "ResultDir's value is invalid")

    url = cfgs.getConfig('GitlabUr')
    task.setData(url + "/data/" + fileName)


def binaryHandler(eventListener: EventListener, letter: Letter) -> None:
    global chooserSet

    import traceback

    if not isinstance(letter, BinaryLetter):
        return None

    try:
        fdSet = eventListener.taskResultFdSet
        tid = letter.getHeader('tid')

        # This is the first binary letter of the task correspond to the
        # received tid just open a file and store the relation into fdSet
        if not tid in chooserSet:
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
    except:
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

def postHandler(eventListener:EventListener, letter: Letter) -> None:

    if not isinstance(letter, CmdResponseLetter):
        return None

    wr = eventListener.getModule(WORKER_ROOM_MOD_NAME) # type: WorkerRoom
    wr.msgToPostManager(letter)

def lisAddrUpdateHandler(eventListener:EventListener, letter:Letter) -> None:
    """
    This handler does not to ensure that that last address
    is successfully sended to worker.

    This Handler may return before send command due to:
    (1) There is no listener may cause of the election is in processed.
    (2) Requested worker is lost after it sended this request
    """
    if not isinstance(letter, ReqLetter):
        return None

    wr = eventListener.getModule(WORKER_ROOM_MOD_NAME) # type: Optional[WorkerRoom]
    if wr is None: return None

    # Get listener's address.
    lis = wr.postListener()
    if lis is None: return None

    addr, port = lis.getAddress()
    command = LisAddrUpdateCmd(addr, port)
    request_from = letter.getIdent()

    wr.control(request_from, command)
