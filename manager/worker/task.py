# task.py

from typing import Optional, Any
from multiprocessing.pool import AsyncResult

class Task:

    """
    Task on client doesn not concern about what it to do
    it just provide a place to query status of a task
    that is processed on client.
    """

    STATE_PENDING = 0
    STATE_PROC = 1
    STATE_TRANSFER = 2
    STATE_DONE = 3

    def __init__(self, tid:str, ver:str, result:AsyncResult, filePath:str) -> None:
        self._tid = tid
        self._asyncResult = result
        self._ver = ver

        self.path = filePath
        self.res = None # type: Optional[Any]

        self._state = Task.STATE_PENDING

    def tid(self) -> str:
        return self._tid

    def version(self) -> str:
        return self._ver

    def isReady(self) -> bool:
        return self._asyncResult.ready()

    def toPendingState(self) -> None:
        self._state = Task.STATE_PENDING

    def toTransferState(self) -> None:
        self._state = Task.STATE_TRANSFER

    def toDoneState(self) -> None:
        self._state = Task.STATE_DONE

    def toProcState(self) -> None:
        self._state = Task.STATE_PROC

    def state(self) -> int:
        return self._state

    def result(self) -> Any:
        if self.res is None:
            self.res = self._asyncResult.get()

        return self.res
