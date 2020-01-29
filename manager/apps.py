import os
import sys

from django.apps import AppConfig

from manager.misc.eventListener import EventListener, responseHandler, binaryHandler,\
    workerRegister
from manager.misc.workerRoom import WorkerRoom
from manager.misc.basic.letter import Letter
from manager.misc.dispatcher import Dispatcher, workerLost_redispatch
from manager.misc.logger import Logger

import manager.misc.components as Components
from manager.misc.basic.info import Info

from manager.misc.exceptions import INVALID_CONFIGURATIONS


initialized = False

predicates = [
    lambda cfgs: "Address" in cfgs,
    lambda cfgs: "Port" in cfgs,
    lambda cfgs: "LogDir" in cfgs,
    lambda cfgs: "ResultDir" in cfgs,
    lambda cfgs: "GitlabUrl" in cfgs,
    lambda cfgs: "PrivateToken" in cfgs,
    lambda cfgs: "TimeZone" in cfgs
]

class ManagerConfig(AppConfig):
    name = 'manager'

    def ready(self):

        if os.environ.get('RUN_MAIN') != 'true':
            return None

        global initialized
        if initialized == False:
            initialized = True
        else:
            return None

        # Load arguments
        configPath = "./config.yaml"

        # Load configuration file
        info = Info(configPath)

        global predicates
        if not info.validityChecking(predicates):
            raise INVALID_CONFIGURATIONS

        Components.config = info

        address = info.getConfig('Address')
        port = info.getConfig('Port')
        logDir = info.getConfig('LogDir')

        # Daemon processes initialization
        workerRoom = WorkerRoom(address, port)
        dispatcher = Dispatcher(workerRoom)
        eventListener = EventListener(workerRoom)
        logger = Logger(logDir)

        eventListener.registerEvent(Letter.Response, responseHandler)
        eventListener.registerEvent(Letter.BinaryFile, binaryHandler)

        # Register hooks into workerRoom
        workerRoom.hookRegister((workerRegister, [eventListener]))
        workerRoom.disconnHookRegister((workerLost_redispatch, [dispatcher]))

        Components.workerRoom = workerRoom
        Components.dispatcher = dispatcher
        Components.eventListener = eventListener
        Components.logger = logger

        # Daemon processes start
        workerRoom.start()
        eventListener.start()
        dispatcher.start()
        logger.start()

        from .misc.verControl import RevSync, revSyncSpawn

        revSyncSpawn(None)
