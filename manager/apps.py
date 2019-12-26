import os

from django.apps import AppConfig

from manager.misc.eventListener import EventListener, responseHandler, binaryHandler,\
    workerRegister
from manager.misc.workerRoom import WorkerRoom
from manager.misc.basic.letter import Letter
from manager.misc.components import Components
from manager.misc.dispatcher import Dispatcher


initialized = False

class ManagerConfig(AppConfig):
    name = 'manager'

    def ready(self):

        if os.environ.get("RUN_MAIN") != 'true':
            return None

        global initialized
        if initialized == False:
            initialized = True
        else:
            return None

        # Daemon processes initialization
        workerRoom = WorkerRoom('127.0.0.1', 8024)
        dispatcher = Dispatcher(workerRoom)
        eventListener = EventListener(workerRoom)

        eventListener.registerEvent(Letter.Response, responseHandler)
        eventListener.registerEvent(Letter.BinaryFile, binaryHandler)

        # Register hooks into workerRoom
        workerRoom.hookRegister((workerRegister, [eventListener]))

        Components.workerRoom = workerRoom
        Components.dispatcher = dispatcher
        Components.eventListener = eventListener

        # Daemon processes start
        workerRoom.start()
        eventListener.start()
        dispatcher.start()

        # Signal registering via decorator
        from .misc.verControl import RevSync
