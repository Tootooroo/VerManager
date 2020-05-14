# task.py

import os

from ..basic.util import pathSeperator
from typing import Optional, Any, BinaryIO
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

    def __init__(self, tid: str, ver: str,
                 result: AsyncResult, filePath: str) -> None:

        self._tid = tid
        self._asyncResult = result
        self._ver = ver

        self.outputFileName = filePath.split(pathSeperator())[-1]
        self.path = filePath
        self.res = None  # type: Optional[Any]

        self._state = Task.STATE_PENDING

        self._fileDesc = None  # type: Optional[BinaryIO]

    def file(self) -> Optional[BinaryIO]:
        if not os.path.exists(self.path):
            return None

        if self._fileDesc is not None:
            return self._fileDesc

        self._fileDesc = open(self.path, "rb")
        return self._fileDesc

    def fileClose(self) -> None:
        if self._fileDesc is None:
            return None

        self._fileDesc.close()
        self._fileDesc = None

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
