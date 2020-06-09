# logger.py

import os

from datetime import datetime
from queue import Queue
from typing import Dict, TextIO, Tuple

from manager.basic.mmanager import ModuleDaemon
from manager.basic.type import State, Ok, Error

from manager.basic.observer import Observer

M_NAME = "Logger"

LOG_ID = str
LOG_MSG = str


class Logger(ModuleDaemon, Observer):

    def __init__(self, path: str) -> None:
        global M_NAME
        ModuleDaemon.__init__(self, M_NAME)
        Observer.__init__(self)

        self.logPath = path
        self.logQueue = Queue(32)  # type: Queue[Tuple[LOG_ID, LOG_MSG]]
        self.logTunnels = {} # type: Dict[str, TextIO]

        if not os.path.exists(path):
            os.mkdir(path)

    def begin(self) -> None:
        return None

    def cleanup(self) -> None:
        return None

    def run(self) -> None:
        while True:
            msgUnit = self.logQueue.get()  # type: Tuple[LOG_ID, LOG_MSG]
            self._output(msgUnit)

    def log_put(self, lid: LOG_ID, msg: LOG_MSG) -> None:
        self.logQueue.put((lid, msg))

    def log_register(self, logId: LOG_ID) -> State:
        if logId in self.logTunnels:
            return Error

        logFilePath = self.logPath + "/" + logId
        file = open(logFilePath, "w")

        self.logTunnels[logId] = file

        return Ok

    def log_close(self, logId: LOG_ID) -> None:
        if logId not in self.logTunnels:
            return None

        fd = self.logTunnels[logId]
        fd.close()

    def _output(self, unit: Tuple[LOG_ID, LOG_MSG]) -> None:
        logId = unit[0]
        logMessage = unit[1]

        if logId not in self.logTunnels:
            return None

        logFile = self.logTunnels[logId]

        logMessage = self._format(logMessage)
        logFile.write(logMessage)
        logFile.flush()

    @staticmethod
    def putLog(log: 'Logger', lid: LOG_ID, msg: LOG_MSG) -> None:
        if log is None:
            return None

        log.log_put(lid, msg)

    @staticmethod
    def _format(message: LOG_MSG) -> str:
        time = datetime.now()
        formated_message = str(time) + " : " + message + '\n'

        return formated_message

    def listenTo(self, data: Tuple[str, str]) -> None:
        tunnelname, msg = data

        if tunnelname not in self.logTunnels:
            self.log_register(tunnelname)

        self.log_put(tunnelname, msg)


# TestCases
import unittest

class LoggerTestCases(unittest.TestCase):
    def test_logger(self):

        from manager.master.logger import Logger

        logger = Logger("./logger")
        logger.start()

        logger.log_register("Test")
        Logger.putLog(logger, "Test", "123")
