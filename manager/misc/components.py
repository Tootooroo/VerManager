# components.py

from typing import *

from manager.misc.dispatcher import Dispatcher
from manager.misc.workerRoom import WorkerRoom
from manager.misc.eventListener import EventListener

class Components:

    dispatcher = None # type: Union[None, Dispatcher]

    workerRoom = None # type: Union[None, WorkerRoom]

    eventListener = None # type: Union[None, EventListener]
