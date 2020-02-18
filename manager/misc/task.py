# task.py

from typing import *
from functools import reduce
from manager.misc.basic.type import *

from manager.misc.build import BuildSet

from datetime import datetime
from threading import Lock

from manager.misc.build import Build, BuildSet

TaskState = int

class Task:

    STATE_PREPARE = 0
    STATE_IN_PROC = 1
    STATE_FINISHED = 2
    STATE_FAILURE = 3

    def __init__(self, id: str, sn:str, vsn:str,
                 build:Optional[Build] = None,
                 buildSet:Optional[BuildSet] = None,
                 extra:Dict[str, str] = {}) -> None:

        self.taskId = id

        self.__parent = None # type: Optional[Task]
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

        self.__build = build
        self.__buildSet = buildSet

        # List of tasks split from this task.
        # This task is done if and only if all subtask
        # of it are done.
        self.__subTasks = [] # type: List['Task']

        if not self.__buildSet is None:
            self.__split()

    # After split this task will be a big task
    def __split(self) -> None:

        if not self.isAbleToSplit():
            return None

        # First, split build set to several builds
        builds = self.__buildSet.getBuilds() # type: ignore

        subTasks = list() # type: List['Task']

        for b in builds:
            t = Task(b.getIdent(), sn = self.__sn, vsn = self.__vsn,
                     build = b,
                     extra = self.__extra)
            t.setParent(self)
            subTasks.append(t)

        self.__subTasks = subTasks

    def setBuild(self, b:Build) -> None:
        self.__build = b

    def setBuildSet(self, bs:BuildSet) -> None:
        self.__buildSet = bs

    def subTasksSpawn(self) -> None:
        if len(self.__subTasks) > 0:
            self.__subTasks = []

        self.__split()

    def isInPost(self, bId:str) -> bool:
        pass

    def getGroupOf(self, tId:str) -> Optional[List['Task']]:
        group = [] # type: List['Task']

        if not self.__buildSet is None:
            builds = self.__buildSet.belongTo(tId)

            if builds is None:
                return None

            for b in builds:
                child = self.getChild(b.getIdent())

                if child is None:
                    return None

                group.append(child)

        return group

    def getChildren(self) -> List['Task']:
        return self.__subTasks

    def getChild(self, cid:str) -> Optional['Task']:
        subTasks = self.__subTasks

        tasks = list(filter(lambda t: t.id() == cid, subTasks))
        if len(tasks) == 0:
            return None

        return tasks[0]

    def hasParent(self) -> bool:
        return not self.__parent is None

    def getParent(self) -> Optional['Task']:
        return self.__parent

    def setParent(self, p:'Task') -> None:
        self.__parent = p

    def isAbleToSplit(self) -> bool:
        return not self.__buildSet is None

    def isBindWithBuild(self) -> bool:
        return not self.__build is None or not self.__buildSet

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

    def toPreState(self, sub:str = "") -> None:
        # all of it's sub tasks in prepare state
        if self.isBigTask():
            f = lambda acc, cur: acc.isPrepare() and cur.isPrepare()
            isAllSubInPre = reduce(f, self.__subTasks)

            if not isAllSubInPre:
                return None

        self.state = Task.STATE_PREPARE

    def toProcState(self) -> None:
        # At least one of it's sub task
        # in proc state
        if self.isBigTask():
            inProcSubs = list(filter(lambda sub: sub.isProc(), self.__subTasks))
            if len(inProcSubs) < 1:
                return None
        self.state = Task.STATE_IN_PROC

    def toFinState(self) -> None:
        # All of it's sub tasks in fin state
        if self.isBigTask():
            f = lambda acc, cur: acc.isFinished() and cur.isFinished()
            isAllSubInFin = reduce(f, self.__subTasks)

            if not isAllSubInFin:
                return None

        self.state = Task.STATE_FINISHED

    def toFailState(self) -> None:
        # At least on of it's sub task
        # in fail state
        if self.isBigTask():
            inFailSubs = list(filter(lambda sub: sub.isFailure(), self.__subTasks))
            if len(inFailSubs) < 1:
                return None

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

    def isBigTask(self) -> bool:
        return not self.__buildSet is None

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
