# Server.py

import manager.master.eventHandlers as EventHandler

from typing import Optional, List
from threading import Thread

from manager.basic.type import State
from manager.basic.mmanager import MManager, Module
from manager.basic.info import Info
from manager.basic.letter import Letter
from manager.master.workerRoom import WorkerRoom, M_NAME as WR_M_NAME
from manager.master.dispatcher import Dispatcher, M_NAME as DISPATCHER_M_NAME
from manager.master.eventListener import EventListener, M_NAME as EVENT_M_NAME
from manager.master.eventHandlers import responseHandler, binaryHandler, \
    logHandler, logRegisterhandler, postHandler, lisAddrUpdateHandler
from manager.master.logger import Logger
from manager.basic.storage import Storage
from manager.master.verControl import RevSync
from manager.master.taskTracker import TaskTracker

ServerInstance = None  # type:  Optional['ServerInst']

predicates = [
    lambda cfgs:  "Address" in cfgs,
    lambda cfgs:  "Port" in cfgs,
    lambda cfgs:  "LogDir" in cfgs,
    lambda cfgs:  "ResultDir" in cfgs,
    lambda cfgs:  "GitlabUrl" in cfgs,
    lambda cfgs:  "PrivateToken" in cfgs,
    lambda cfgs:  "TimeZone" in cfgs
]


class ServerInst(Thread):

    def __init__(self, address: str, port: int, cfgPath: str) -> None:
        Thread.__init__(self)
        self._address = address
        self._port = port

        self._configPath = cfgPath

        self._mmanager = MManager()

    def getModule(self, m: str) -> Optional[Module]:
        return self._mmanager.getModule(m)

    def addModule(self, mod: Module) -> State:
        return self._mmanager.addModule(mod)

    def modules(self) -> List[Module]:
        return self._mmanager.getAllModules()

    def run(self) -> None:
        global predicates

        info = Info(self._configPath)

        # if not info.validityChecking(predicates):
        #    raise INVALID_CONFIGURATIONS

        self.addModule(info)

        workerRoom = WorkerRoom(self._address, self._port, self)
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

        EventHandler.EVENT_HANDLER_TOOLS.action_init(eventListener)

        logDir = info.getConfig('LogDir')
        logger = Logger(logDir)
        self.addModule(logger)

        storage = Storage(info.getConfig('Storage'), self)
        self.addModule(storage)

        revSyncner = RevSync(self)
        self.addModule(revSyncner)

        # Subscribe to subjects
        eventListener.subscribe(EventListener.NOTIFY_LOST, workerRoom)
        workerRoom.subscribe(WorkerRoom.NOTIFY_CONN, eventListener)
        workerRoom.subscribe(WorkerRoom.NOTIFY_DISCONN, dispatcher)

        workerRoom.subscribe(WorkerRoom.NOTIFY_LOG, logger)
        eventListener.subscribe(EventListener.NOTIFY_LOG, logger)
        dispatcher.subscribe(Dispatcher.NOTIFY_LOG, logger)

        # Install observer handlers to EventListener
        async def new_worker_register(data):
            await eventListener.workerRegister(data)
        eventListener.handler_install(WR_M_NAME, new_worker_register)

        # Install observer handlers to WorkerRoom
        async def wr_handler_disconn(data):
            await workerRoom.notifyEvent(WorkerRoom.EVENT_DISCONNECTED, data)
        workerRoom.handler_install(EVENT_M_NAME, wr_handler_disconn)

        # Install observer handlers to Dispatcher
        async def handler_dispatcher(data):
            await dispatcher.workerLost_redispatch(data)
        dispatcher.handler_install(WR_M_NAME, handler_dispatcher)

        # Install log handler to logger
        for module in [EVENT_M_NAME, WR_M_NAME, DISPATCHER_M_NAME]:
            logger.handler_install(module, logger.listenTo)
