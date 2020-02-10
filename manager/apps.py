import os
import sys

from django.apps import AppConfig

from manager.misc.eventHandlers import responseHandler, binaryHandler
from manager.misc.eventListener import EventListener, workerRegister
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
