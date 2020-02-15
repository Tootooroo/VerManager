# task.py

from typing import *
from manager.misc.basic.type import *

from datetime import datetime
from threading import Lock

TaskState = int

class Task:

    STATE_PREPARE = 0
    STATE_IN_PROC = 1
    STATE_FINISHED = 2
    STATE_FAILURE = 3

    def __init__(self, id: str, sn:str, vsn:str, extra:Dict[str, str] = {}) -> None:
        self.taskId = id

        self.__sn = sn
        self.__vsn = vsn
        self.__extra = extra

        self.state = Task.STATE_PREPARE

        # This field will be set by EventListener while
        # the task is complete by worker and transfer
        # totally
        self.data = ""

        # Indicate that the number of client request to the task
        self.refs = 0

        self.lastAccess = datetime.utcnow()

    def getExtra(self) -> Optional[Dict[str, str]]:
        return self.__extra

    def getSN(self) -> str:
        return self.__sn

    def getVSN(self) -> str:
        return self.__vsn

    def id(self) -> str:
        return self.taskId

    def lastUpdate(self) -> None:
        self.lastAccess = datetime.utcnow()

    def last(self) -> datetime:
        return self.lastAccess

    def taskState(self) -> TaskState:
        return self.state

    def stateChange(self, state:int) -> None:
        self.state = state

    def toPreState(self) -> None:
        self.state = Task.STATE_PREPARE

    def toProcState(self) -> None:
        self.state = Task.STATE_IN_PROC

    def toFinState(self) -> None:
        self.state = Task.STATE_FINISHED

    def toFailState(self) -> None:
        self.state = Task.STATE_FAILURE

    def setData(self, data: str) -> None:
        self.data = data

    def isPrepare(self) -> bool:
        return self.state == Task.STATE_PREPARE

    def isProc(self) -> bool:
        return self.state == Task.STATE_IN_PROC

    def isFailure(self) -> bool:
        return self.state == Task.STATE_FAILURE

    def isFinished(self) -> bool:
        return self.state == Task.STATE_FINISHED

    @staticmethod
    def isValidState(s:int) -> bool:
        return s >= Task.STATE_PREPARE and s <= Task.STATE_FAILURE

# Every task in TaskGroup must be unique in the TaskGroup
class TaskGroup:
    def __init__(self) -> None:
        self.__dict_tasks = {} # type: Dict[str, Task]
        self.__numOfTasks = 0
        self.__lock = Lock()

    def newTask(self, task: Task) -> None:
        tid = task.id()

        with self.__lock:
            if tid in self.__dict_tasks:
                return None

            self.__dict_tasks[task.id()] = task
            self.__numOfTasks += 1

    def remove(self, id: str) -> State:
        with self.__lock:
            if not id in self.__dict_tasks:
                return Error

            del self.__dict_tasks [id]
            self.__numOfTasks -= 1
            return Ok

    def __mark(self, id: str, st: TaskState) -> State:
        task = self.search(id)
        if task is None:
            return Error
        task.stateChange(st)

        return Ok

    def toList(self) -> List[Task]:
        return list(self.__dict_tasks.values())

    def toList_(self) -> List[str]:
        l = self.toList()
        l_id = map(lambda t: t.id(), l)

        return list(l_id)

    def markPre(self, id: str) -> State:
        return self.__mark(id, Task.STATE_PREPARE)

    def markInProc(self, id:str) -> State:
        return self.__mark(id, Task.STATE_IN_PROC)

    def markFin(self, id: str) -> State:
        return self.__mark(id, Task.STATE_FINISHED)

    def markFail(self, id: str) -> State:
        return self.__mark(id, Task.STATE_FAILURE)

    def search(self, id: str) -> Union[Task, None]:
        with self.__lock:
            if not id in self.__dict_tasks:
                return None

            return self.__dict_tasks[id]

    def numOfTasks(self) -> int:
        return self.__numOfTasks
