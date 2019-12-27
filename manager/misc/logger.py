# logger.py

from datetime import datetime

from typing import *
from manager.misc.basic.letter import Letter
from manager.misc.basic.type import *

from queue import Queue
from threading import Thread

class Logger(Thread):

    def __init__(self, path: str) -> None:
        Thread.__init__(self)

        self.logPath = path
        self.logQueue = Queue(32) # type: Queue[Letter]
        self.logTunnels = {} # type: Dict[str, TextIO]

    def run(self) -> None:

        while True:

            letter = self.logQueue.get()

            if letter.typeOfLetter() == Letter.Log:
                self.log_register(letter)
            elif letter.typeOfLetter() == Letter.LogRegister:
                logId = letter.getHeader('logId')
                self.__output(logId, letter)

    def log_put(self, letter: Letter) -> None:
        self.logQueue.put(letter)

    def log_register(self, letter: Letter) -> State:
        logId = letter.getHeader('logId')

        if logId in self.logTunnels:
            return Error

        logFilePath = self.logPath + "/" + logId
        file = open(logFilePath, "w")

        self.logTunnels[logId] = file

        return Ok

    def __output(self, logId, letter: Letter) -> None:
        logFile = self.logTunnels[logId]

        logMessage = letter.getContent('logMsg')
        if isinstance(logMessage, str):
            logMessage = self.__format(logMessage)
            logFile.write(logMessage)

    @staticmethod
    def __format(message: str) -> str:
        time = datetime.now()
        formated_message = str(time) + " : " + message

        return formated_message
