# task.py

from typing import Optional
from multiprocessing.pool import AsyncResult

class Task:

    STATE_PENDING = 0
    STATE_PROC = 1
    STATE_TRANSFER = 2

    def __init__(self, tid:str, ver:str, result:AsyncResult) -> None:
        self._tid = tid
        self._asyncResult = result
        self._ver = ver

        # File name of the file
        # generated by process of the task
        self.file = None # type: Optional[str]

        self._state = Task.STATE_PENDING

    def isReady(self) -> bool:
        return self._asyncResult.ready()

    def toPendingState(self) -> None:
        self._state = Task.STATE_PENDING

    def toTransferState(self) -> None:
        self._state = Task.STATE_TRANSFER

    def toProcState(self) -> None:
        self._state = Task.STATE_PROC

    def state(self) -> int:
        return self._state
