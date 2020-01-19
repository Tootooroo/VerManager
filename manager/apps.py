import os

from django.apps import AppConfig

from manager.misc.eventListener import EventListener, responseHandler, binaryHandler,\
    workerRegister
from manager.misc.workerRoom import WorkerRoom
from manager.misc.basic.letter import Letter
from manager.misc.dispatcher import Dispatcher, workerLost_redispatch
from manager.misc.logger import Logger

import manager.misc.components as Components


initialized = False

class ManagerConfig(AppConfig):
    name = 'manager'

    def ready(self):

        global initialized
        if initialized == False:
            initialized = True
        else:
            return None

        # Load arguments
        configPath = sys.argv[1]

        # Load configuration file
        info = Info(configPath)
        Components.config = info

        port = info.getConfig('Port')
        logDir = info.getConfig('LogDir')

        # Daemon processes initialization
        workerRoom = WorkerRoom('0.0.0.0', port)
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
