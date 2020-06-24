# logger.py

import os
import asyncio

from datetime import datetime
from queue import Queue
from typing import Dict, TextIO, Tuple, Optional

from manager.basic.mmanager import ModuleDaemon
from manager.basic.type import State, Ok, Error

from manager.basic.observer import Observer

M_NAME = "Logger"

LOG_ID = str
LOG_MSG = str

class LOGGER_NOT_EXISTS(Exception):
    pass


class Logger(ModuleDaemon, Observer):

    def __init__(self, path: str) -> None:
        global M_NAME
        ModuleDaemon.__init__(self, M_NAME)
        Observer.__init__(self)

        self.logPath = path
        self.logQueue = None  \
            # type: Optional[asyncio.Queue[Tuple[LOG_ID, LOG_MSG]]]

        self.logTunnels = {} # type: Dict[str, TextIO]

        self._stop = False

        if not os.path.exists(path):
            os.mkdir(path)

    async def begin(self) -> None:
        self.logQueue = asyncio.Queue(128)

    async def cleanup(self) -> None:
        self.logQueue = None
        self.logTunnels = {}

    async def run(self) -> None:

        if self.logQueue is None:
            return None

        while True:
            if self._stop: return None

            msgUnit = await self.logQueue.get()  # type: Tuple[LOG_ID, LOG_MSG]
            self._output(msgUnit)

    async def stop(self) -> None:
        self._stop = True

    def needStop(self) -> bool:
        return self._stop

    async def log_put(self, lid: LOG_ID, msg: LOG_MSG) -> None:
        if self.logQueue is None:
            raise LOGGER_NOT_EXISTS()

        await self.logQueue.put((lid, msg))

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
    async def putLog(log: 'Logger', lid: LOG_ID, msg: LOG_MSG) -> None:
        if log is None:
            return None

        await log.log_put(lid, msg)

    @staticmethod
    def _format(message: LOG_MSG) -> str:
        time = datetime.now()
        formated_message = str(time) + " : " + message + '\n'

        return formated_message

    async def listenTo(self, data: Tuple[str, str]) -> None:
        tunnelname, msg = data

        if tunnelname not in self.logTunnels:
            self.log_register(tunnelname)

        await self.log_put(tunnelname, msg)


# TestCases
import unittest

class LoggerTestCases(unittest.TestCase):

    def test_logger(self):

        from manager.master.logger import Logger

        logger = Logger("./logger")

        async def loggerDaemon(logger: Logger) -> None:
            await logger.begin()
            await logger.start()

        async def loggerUser(logger: Logger) -> None:
            logger.log_register("Test")
            await Logger.putLog(logger, "Test", "123")

            await logger.stop()

        async def test() -> None:
            await asyncio.gather(
                loggerDaemon(logger),
                loggerUser(logger)
            )

        asyncio.run(test())
