# Server.py

from typing import *
from socket import *
from threading import Thread

from manager.basic.type import Ok, Error, State
from manager.basic.mmanager import MManager, Module
from manager.basic.info import Info
from manager.basic.letter import Letter
from manager.master.workerRoom import WorkerRoom
from manager.master.dispatcher import Dispatcher, workerLost_redispatch
from manager.master.eventListener import EventListener, workerRegister
from manager.master.eventHandlers import responseHandler, binaryHandler, \
    logHandler, logRegisterhandler, postHandler
from manager.master.logger import Logger, M_NAME as LOGGER_M_NAME
from manager.basic.storage import Storage
from manager.master.exceptions import INVALID_CONFIGURATIONS
from manager.master.verControl import RevSync

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

        dispatcher = Dispatcher(workerRoom, self)
        self.addModule(dispatcher)

        eventListener = EventListener(workerRoom, self)
        eventListener.registerEvent(Letter.Response, responseHandler)
        eventListener.registerEvent(Letter.BinaryFile, binaryHandler)
        eventListener.registerEvent(Letter.CmdResponse, postHandler)
        self.addModule(eventListener)

        logger = Logger("./logger")
        self.addModule(logger)

        storage = Storage(info.getConfig('Storage'), self)
        self.addModule(storage)

        revSyncner = RevSync(self)

        workerRoom.hookRegister((workerRegister, [eventListener]))
        workerRoom.disconnHookRegister((workerLost_redispatch, [dispatcher]))

        self.__mmanager.startAll()

        # Block the initial thread cause the entire program
        # exists when only daemon-thread exists. initial thread
        # is the only one non-daemon thread.
        self.__mmanager.join()
