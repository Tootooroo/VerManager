# components.py

from typing import *

from manager.misc.dispatcher import Dispatcher
from manager.misc.workerRoom import WorkerRoom
from manager.misc.eventListener import EventListener

class Components:

    dispatcher = None # type: Optional[Dispatcher]

    workerRoom = None # type: Optional[WorkerRoom]

    eventListener = None # type: Optional[EventListener]
