# Server.py

from typing import *
from socket import *

from threading import Thread

from manager.misc.basic.info import Info

from manager.misc.basic.letter import Letter

from manager.misc.workerRoom import WorkerRoom
from manager.misc.dispatcher import Dispatcher

from manager.misc.eventListener import EventListener, workerRegister
from manager.misc.eventHandlers import responseHandler, binaryHandler, logHandler, logRegisterhandler

from manager.misc.logger import Logger

from manager.misc.storage import Storage

from manager.misc.exceptions import INVALID_CONFIGURATIONS

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

    def __init__(self, address:str, port:int, cfgPath:str, modules:Dict[str, bool] = None) -> None:
        Thread.__init__(self)

        self.__address = address
        self.__port = port

        self.__configPath = cfgPath

        self.__modEnable = modules

        self.__modules = {} # type: Dict[str, Any]

    def isModuleEnable(self, m:str) -> bool:
        if self.__modEnable is None:
            return True

        if m not in self.__modEnable:
            return True

        return self.__modEnable[m]

    def getModule(self, m:str) -> Any:
        if not m in self.__modules:
            return None

        return self.__modules[m]

    def addModule(self, m:str, mod:Any) -> None:
        if m in self.__modules:
            return None

        self.__modules[m] = mod

    def modules(self) -> List:
        return list(self.__modules.values())

    def run(self) -> None:
        global predicates

        info = Info(self.__configPath)

        if not info.validityChecking(predicates):
            raise INVALID_CONFIGURATIONS

        self.addModule('Config', info)

        workerRoom = WorkerRoom(self.__address, self.__port, self)
        self.addModule('WorkerRoom', workerRoom)

        dispatcher = Dispatcher(workerRoom, self)
        self.addModule('Dispatcher', dispatcher)

        eventListener = EventListener(workerRoom, self)
        eventListener.registerEvent(Letter.Response, responseHandler)
        eventListener.registerEvent(Letter.BinaryFile, binaryHandler)
        self.addModule('EventListener', eventListener)

        logger = Logger("./logger")
        self.addModule('Logger', logger)

        storage = Storage(info.getConfig('ResultDir'), self)
        self.addModule('Storage', storage)

        workerRoom.hookRegister((workerRegister, [eventListener]))

        if self.isModuleEnable('WorkerRoom'):
            workerRoom.start()

        if self.isModuleEnable('EventListener'):
            eventListener.start()

        if self.isModuleEnable('Dispatcher'):
            dispatcher.start()

        if self.isModuleEnable('Logger'):
            logger.start()

        modules = self.modules()

        # Join to modules
        for m in modules:
            if not isinstance(m, Thread):
                continue

            m.join()
