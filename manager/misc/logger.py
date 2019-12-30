# logger.py

from datetime import datetime

from typing import *
from manager.misc.basic.letter import Letter
from manager.misc.basic.type import *

from queue import Queue
from threading import Thread

import os

LOG_ID = str
LOG_MSG = str

class Logger(Thread):

    def __init__(self, path: str) -> None:
        Thread.__init__(self)

        self.logPath = path
        self.logQueue = Queue(32) # type: Queue[Tuple[LOG_ID, LOG_MSG]]
        self.logTunnels = {} # type: Dict[str, TextIO]

        if not os.path.exists(path):
            os.mkdir(path)

    def run(self) -> None:

        while True:

            msgUnit = self.logQueue.get() # type: Tuple[LOG_ID, LOG_MSG]
            print(msgUnit)
            self.__output(msgUnit)

    def log_put(self, msg:Tuple[LOG_ID, LOG_MSG]) -> None:
        self.logQueue.put(msg)

    def log_register(self, logId: LOG_ID) -> State:
        if logId in self.logTunnels:
            return Error

        logFilePath = self.logPath + "/" + logId
        file = open(logFilePath, "w")

        self.logTunnels[logId] = file

        return Ok

    def __output(self, unit: Tuple[LOG_ID, LOG_MSG]) -> None:
        logId = unit[0]
        logMessage = unit[1]

        logFile = self.logTunnels[logId]

        logMessage = self.__format(logMessage)
        logFile.write(logMessage)
        logFile.flush()

    @staticmethod
    def __format(message: LOG_MSG) -> str:
        time = datetime.now()
        formated_message = str(time) + " : " + message + '\n'

        return formated_message
