# task.py

from typing import *
from manager.misc.basic.type import *

TaskState = int

class Task:

    STATE_PREPARE = 0
    STATE_IN_PROC = 1
    STATE_FINISHED = 2
    STATE_FAILURE = 3

    def __init__(self, id: str, content: Dict) -> None:
        self.taskId = id

        self.content = content
        self.state = Task.STATE_PREPARE

        # This field will be set by EventListener while
        # the task is complete by worker and transfer
        # totally
        self.data = ""

        # Indicate that the number of client request to the task
        self.refs = 0

    def id(self) -> str:
        return self.taskId

    def taskState(self) -> TaskState:
        return self.state

    def stateChange(self, state: TaskState) -> None:
        self.state = state

    def setData(self, data: str) -> None:
        self.data = data

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

    def newTask(self, task: Task) -> None:
        self.__dict_tasks[task.id()] = task
        self.__numOfTasks += 1

    def remove(self, id: str) -> State:
        if id in self.__dict_tasks:
            del self.__dict_tasks [id]
            return Ok
        return Error

    def __mark(self, id: str, st: TaskState) -> State:
        task = self.search(id)
        if task is None:
            return Error
        task.stateChange(st)

        return Ok

    def toList(self) -> List[Task]:
        return list(self.__dict_tasks.values())

    def markPre(self, id: str) -> State:
        return self.__mark(id, Task.STATE_PREPARE)

    def markInProc(self, id:str) -> State:
        return self.__mark(id, Task.STATE_IN_PROC)

    def markFin(self, id: str) -> State:
        return self.__mark(id, Task.STATE_FINISHED)

    def markFail(self, id: str) -> State:
        return self.__mark(id, Task.STATE_FAILURE)

    def search(self, id: str) -> Union[Task, None]:
        if not id in self.__dict_tasks:
            return None

        return self.__dict_tasks[id]
