# EventHandlers

import zipfile
import shutil

from manager.master.eventListener import EventListener, letterLog

from manager.basic.letter import *
from manager.master.task import Task

from manager.basic.commands import PostConfigCmd
from manager.basic.storage import Storage, StoChooser
from manager.master.logger import Logger

from manager.master.workerRoom import WorkerRoom
from manager.master.workerRoom import M_NAME as WORKER_ROOM_MOD_NAME
from manager.master.postElection import PostManager, Role_Listener

def packDataWithChangeLog(vsn: str, filePath: str, dest: str, log_start:str = "", log_end:str = "") -> str:
    from manager.models import infoBetweenRev, Versions

    changeLog = infoBetweenRev(log_start, log_end)

    with open("./log.txt", "w") as logFile:
        for log in changeLog:
            logFile.write(log)

    zipFileName = vsn + "_with_log.rar"

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

    workers = eventListener.getModule('WorkerRoom')
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

    # Close chooser
    chooser = chooserSet[taskId]
    chooser.close()
    del chooserSet [taskId]

    # Pending feature
    # Store result to the target position specified in configuration file
    # Send email to notify that task id done
    try:
        cfgs = eventListener.getModule('Config')
        resultDir = cfgs.getConfig("ResultDir")

        dispatcher = eventListener.getModule('Dispatcher')

        task = dispatcher.getTask(taskId)
        if task is None:
            return None

        extra = task.getExtra()

        if "logFrom" in extra and "logTo" in extra:
            destFileName = packDataWithChangeLog(taskId,
                                                 chooser.path(), resultDir,
                                                 extra['logFrom'], extra['logTo'])
        else:
            path = chooser.path()
            destFileName = path.split("/")[-1] + "_without_log.rar"
            destFilePath = shutil.copy(chooser.path(),
                                       resultDir+"/"+destFileName)

    except FileNotFoundError:
        logger = eventListener.getModule('Logger')
        Logger.putLog(logger, letterLog, "ResultDir's value is invalid")

    workers = eventListener.getModule('WorkerRoom')
    worker = workers.getWorker(ident)

    if worker is None:
        return None

    task = worker.searchTask(taskId)

    if task is None:
        return None

    config = eventListener.getModule('Config')
    url = config.getConfig('GitlabUr')
    task.setData(url + "/static/" + destFileName)


def binaryHandler(eventListener: EventListener, letter: Letter) -> None:
    global chooserSet

    import traceback

    try:
        fdSet = eventListener.taskResultFdSet
        tid = letter.getHeader('tid')

        # This is the first binary letter of the task correspond to the
        # received tid just open a file and store the relation into fdSet
        if not tid in chooserSet:
            extension = letter.getHeader('extension')

            sto = eventListener.getModule('Storage')
            chooser = sto.create(tid, extension)
            chooserSet[tid] = chooser

        chooser = chooserSet[tid]
        content = letter.getContent('bytes')

        if isinstance(content, str):
            return None

        chooser.store(content)
    except:
        traceback.print_exc()

def logHandler(eventListener: EventListener, letter: Letter) -> None:
    logger = eventListener.getModule('Logger')

    logId = letter.getHeader('logId')
    logMsg = letter.getContent('logMsg')

    if isinstance(logMsg, str):
        Logger.putLog(logger, logId, logMsg)

def logRegisterhandler(eventListener: EventListener, letter: Letter) -> None:
    logger = eventListener.getModule('Logger')

    logId = letter.getHeader('logId')
    logger.log_register(logId)

def postHandler(eventListener:EventListener, letter: Letter) -> None:

    if not isinstance(letter, CmdResponseLetter):
        return None

    pManager = eventListener.getModule(WORKER_ROOM_MOD_NAME) # type: WorkerRoom
    assert(isinstance(pManager, PostManager))

    workerName = letter.getIdent()
    role = letter.getExtra('role')

    if role is PostConfigCmd.ROLE_LISTENER:
        pManager.setRole(workerName, Role_Listener)
