# EventHandlers

import zipfile
import shutil

from manager.misc.eventListener import EventListener, letterLog

from manager.misc.basic.letter import *
from manager.misc.task import Task

from manager.misc.storage import Storage, StoChooser
from manager.misc.logger import Logger

def packDataWithChangeLog(vsn: str, filePath: str, dest: str, log_start:str = "", log_end:str = "") -> str:
    from manager.models import infoBetweenVer, Versions

    changeLog = infoBetweenVer(log_start, log_end)

    with open("./log.txt", "w") as logFile:
        for log in changeLog:
            logFile.write(log)

    zipFileName = vsn + "with_log.rar"

    zipFd = zipfile.ZipFile(dest + "/" + zipFileName, "w")
    for aFile in ["./log.txt", filePath]:
        zipFd.write(aFile)
    zipFd.close()

    return zipFileName

chooserSet = {} # type: Dict[str, StoChooser]

def responseHandler(eventListener:EventListener, letter:Letter) -> None:

    if letter.typeOfLetter() != Letter.Response:
        return None

    ident = letter.getHeader('ident')
    taskId = letter.getHeader('tid')
    state = int(letter.getContent('state'))

    workers = eventListener.refToModule('WorkerRoom')
    worker = workers.getWorker(ident)

    if worker is None:
        return None

    task = worker.searchTask(taskId)

    if not task is None and Task.isValidState(state):
        if state == Task.STATE_FINISHED:

            responseHandler_ResultStore(eventListener, letter)

            worker.removeTask(taskId)
        task.stateChange(state)

def responseHandler_ResultStore(eventListener: EventListener, letter: Letter) -> None:

    global chooserSet

    # Should verify the letter's format
    ident = letter.getHeader('ident')
    taskId = letter.getHeader('tid')
    state = int(letter.getContent('state'))

    if Task.isValidState(state) and state != Task.STATE_FINISHED:
        return None

    chooser = chooserSet[taskId]
    chooser.close()

    # Pending feature
    # Store result to the target position specified in configuration file
    # Send email to notify that task id done
    try:
        cfgs = eventListener.refToModule('Config')
        resultDir = cfgs.getConfig("ResultDir")

        dispatcher = eventListener.refToModule('Dispatcher')

        task = dispatcher.getTask(taskId)
        if task is None:
            return None

        extra = task.getExtra()

        if not extra is None:
            destFileName = packDataWithChangeLog(taskId,
                                                 chooser.path(), resultDir,
                                                 extra['logStart'], extra['logEnd'])
        else:
            destFilePath = shutil.copy(chooser.path(), resultDir)
            destFileName = destFilePath.split("/")[-1]

    except FileNotFoundError:
        logger = eventListener.refToModule('Logger')
        Logger.putLog(logger, letterLog, "ResultDir's value is invalid")

    workers = eventListener.refToModule('WorkerRoom')
    worker = workers.getWorker(ident)

    if worker is None:
        return None

    task = worker.searchTask(taskId)

    if task is None:
        return None

    config = eventListener.refToModule('Config')
    url = config.getConfig('GitlabUr')
    task.setData(url + "/static/" + destFileName)


def binaryHandler(eventListener: EventListener, letter: Letter) -> None:
    global chooserSet

    fdSet = eventListener.taskResultFdSet
    tid = letter.getHeader('tid')

    # This is the first binary letter of the task correspond to the
    # received tid just open a file and store the relation into fdSet
    if not tid in chooserSet:
        sto = eventListener.refToModule('Storage')
        chooser = sto.open(tid)
        chooserSet[tid] = chooser

    chooser = chooserSet[tid]
    content = letter.getContent('bytes')

    if isinstance(content, str):
        return None

    chooser.store(content)

def logHandler(eventListener: EventListener, letter: Letter) -> None:
    logger = eventListener.refToModule('Logger')

    logId = letter.getHeader('logId')
    logMsg = letter.getContent('logMsg')

    if isinstance(logMsg, str):
        Logger.putLog(logger, logId, logMsg)

def logRegisterhandler(eventListener: EventListener, letter: Letter) -> None:
    logger = eventListener.refToModule('Logger')

    logId = letter.getHeader('logId')
    logger.log_register(logId)
