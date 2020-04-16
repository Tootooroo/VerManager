# Server.py

from typing import *
from socket import *
from threading import Thread

from manager.basic.type import Ok, Error, State
from manager.basic.mmanager import MManager, Module
from manager.basic.info import Info
from manager.basic.letter import Letter
from manager.master.workerRoom import WorkerRoom, M_NAME as WR_M_NAME
from manager.master.dispatcher import Dispatcher, M_NAME as DISPATCHER_M_NAME, \
    workerLost_redispatch
from manager.master.eventListener import EventListener, workerRegister, M_NAME as EVENT_M_NAME
from manager.master.eventHandlers import responseHandler, binaryHandler, \
    logHandler, logRegisterhandler, postHandler, lisAddrUpdateHandler
from manager.master.logger import Logger, M_NAME as LOGGER_M_NAME
from manager.basic.storage import Storage
from manager.master.exceptions import INVALID_CONFIGURATIONS
from manager.master.verControl import RevSync
from manager.master.taskTracker import TaskTracker

from manager.basic.info import M_NAME as INFO_M_NAME

ServerInstance = None # type: Optional['ServerInst']

predicates = [
    lambda cfgs: "Address" in cfgs,
    lambda cfgs: "Port" in cfgs,
    lambda cfgs: "LogDir" in cfgs,
    lambda cfgs: "ResultDir" in cfgs,
    lambda cfgs: "GitlabUrl" in cfgs,
    lambda cfgs: "PrivateToken" in cfgs,
    lambda cfgs: "TimeZone" in cfgs
]

class ServerInst(Thread):

    def __init__(self, address:str, port:int, cfgPath:str) -> None:
        Thread.__init__(self)
        self.__address = address
        self.__port = port

        self.__configPath = cfgPath

        self.__mmanager = MManager()

    def getModule(self, m:str) -> Optional[Module]:
        return self.__mmanager.getModule(m)

    def addModule(self, mod:Module) -> State:
        return self.__mmanager.addModule(mod)

    def modules(self) -> List[Module]:
        return self.__mmanager.getAllModules()

    def run(self) -> None:
        global predicates

        info = Info(self.__configPath)

        #if not info.validityChecking(predicates):
        #    raise INVALID_CONFIGURATIONS

        self.addModule(info)

        workerRoom = WorkerRoom(self.__address, self.__port, self)
        self.addModule(workerRoom)

        tracker = TaskTracker()
        self.addModule(tracker)

        dispatcher = Dispatcher(workerRoom, self)
        self.addModule(dispatcher)

        eventListener = EventListener(self)
        eventListener.registerEvent(Letter.Response, responseHandler)
        eventListener.registerEvent(Letter.BinaryFile, binaryHandler)
        eventListener.registerEvent(Letter.CmdResponse, postHandler)
        eventListener.registerEvent(Letter.LogRegister, logRegisterhandler)
        eventListener.registerEvent(Letter.Log, logHandler)
        eventListener.registerEvent(Letter.Req, lisAddrUpdateHandler)
        self.addModule(eventListener)

        logDir = info.getConfig('LogDir')
        logger = Logger(logDir)
        self.addModule(logger)

        storage = Storage(info.getConfig('Storage'), self)
        self.addModule(storage)

        revSyncner = RevSync(self)
        self.addModule(revSyncner)

        # Subscribe to subjects
        eventListener.subscribe(workerRoom)
        workerRoom.subscribe(eventListener)
        workerRoom.subscribe(dispatcher)
        dispatcher.subscribe(workerRoom)

        # Install observer handlers to EventListener
        eventListener.handler_install(WR_M_NAME, lambda data: workerRegister(eventListener, data))

        # Install observer handlers to WorkerRoom
        wr_handler_disconn = lambda data: workerRoom.notifyEventFd(WorkerRoom.EVENT_DISCONNECTED,
                                                              data)
        workerRoom.handler_install(EVENT_M_NAME, wr_handler_disconn)
        workerRoom.handler_install(DISPATCHER_M_NAME, lambda data: workerRoom.tasks_clear())

        # Install observer handlers to Dispatcher
        handler_dispatcher = lambda data: workerLost_redispatch(dispatcher, data)
        dispatcher.handler_install(WR_M_NAME, handler_dispatcher)

        self.__mmanager.startAll()

        # Block the initial thread cause the entire program
        # exists when only daemon-thread exists. initial thread
        # is the only one non-daemon thread.
        self.__mmanager.join()
