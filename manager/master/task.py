# task.py

from typing import *
from functools import reduce
from manager.basic.type import Ok, Error, State
from manager.basic.letter import NewLetter, Letter, PostTaskLetter

from manager.master.build import BuildSet

from datetime import datetime
from threading import Lock

from manager.master.build import Build, BuildSet, Post, Merge

TaskState = int

TaskType = int

class TASK_TRANSFORM_ERROR(Exception): pass

class Task:

    STATE_PREPARE = 0
    STATE_IN_PROC = 1
    STATE_FINISHED = 2
    STATE_FAILURE = 3
    STATE_POST = 4

    def __init__(self, type:TaskType, id: str, sn:str, vsn:str,
                 extra:Dict[str, str] = {}) -> None:

        self.taskId = id

        self.type = type
        self.sn = sn
        self.vsn = vsn
        self.extra = extra

        # Files that relate to this task
        self.__files = None  # type: Optional[BinaryIO]

        self.state = Task.STATE_PREPARE

        # This field will be set by EventListener while
        # the task is complete by worker and transfer
        # back totally.
        self.data = ""

        self.build = None # type: Optional[Union[Build, BuildSet]]

        # Indicate that the number of request to the task
        self.refs = 0

        self.lastAccess = datetime.utcnow()

    def getType(self) -> TaskType:
        return self.type

    def setType(self, type:TaskType) -> None:
        self.type = type

    def getExtra(self) -> Optional[Dict[str, str]]:
        return self.extra

    def getSN(self) -> str:
        return self.sn

    def getVSN(self) -> str:
        return self.vsn

    def id(self) -> str:
        return self.taskId

    def lastUpdate(self) -> None:
        self.lastAccess = datetime.utcnow()

    def last(self) -> datetime:
        return self.lastAccess

    def taskState(self) -> TaskState:
        return self.state

    def setBuild(self, b:Union[Build, BuildSet]) ->  None:
        self.build = b

    def isBindWithBuild(self) -> bool:
        return self.build is not None

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

    # fixme: Python 3.5.3 raise an NameError exception:
    #        name 'BinaryIO' is not defined. Temporarily
    #        use Any to instead of BinaryIO
    def file(self) -> Optional[Any]:
        return self.__files

    def toLetter(self) -> Letter:
        pass

    @staticmethod
    def isValidState(s:int) -> bool:
        return s >= Task.STATE_PREPARE and s <= Task.STATE_POST

    def transform(self) -> 'Task':

        if isinstance(self.build, Build):
            return SingleTask(self.id(), self.sn, self.vsn, self.build, self.extra)
        elif isinstance(self.build, BuildSet):
            return SuperTask(self.id(), self.sn, self.vsn, self.build)

        raise TASK_TRANSFORM_ERROR

class SuperTask(Task):

    Type = 0

    def __init__(self, id:str, sn:str, revision:str, buildSet:BuildSet) -> None:

        Task.__init__(self, SuperTask.Type, id, sn, revision)

        self.__children = [] # type: List['Task']
        self.__buildSet = buildSet

        self.__split()

    def getChildren(self) -> List[Task]:
        return self.__children

    def getChild(self, ident:str) -> Optional[Task]:
        maybe_the_child = list(
            filter(lambda w: w.id() == ident, self.__children))

        count = len(maybe_the_child)
        if count is 1:
            return maybe_the_child[0]

        return None

    def getGroupOf(self, tid:str) -> Optional[List[Task]]:
        group = []  # type: List[Task]

        builds = self.__buildSet.belongTo(tid)
        if builds is None:
            return None

        builds_list = builds[1]

        for b in builds_list:
            child = self.getChild(b.getIdent())

            if child is None:
                return None

            group.append(child)

        return group

    # For SuperTask isBindWithBuild should always return True
    def isBindWithBuild(self) -> bool:
        return self.__buildSet is not None

    def toPreState(self) -> None:
        f = lambda acc, cur: acc.isPrepare() and cur.isPrepare()

        isAbleTo = reduce(f, self.__children)

        if isAbleTo:
            self.state = Task.STATE_PREPARE

    def toFinState(self) -> None:
        f = lambda acc, cur: acc.isFinished() and cur.isFinished()

        isAbleTo = reduce(f, self.__children)
        if isAbleTo:
            self.state = Task.STATE_FINISHED

    def toFailState(self) -> None:
        failedChildren = list(filter(lambda child: child.isFailure(), self.__children))

        if len(failedChildren) > 0:
            self.state = Task.STATE_FAILURE

    def setBuildSet(self, buildSet:BuildSet) -> None:
        self.__buildSet = buildSet

    def getPostTask(self) -> Optional['PostTask']:
        for child in self.__children:
            if isinstance(child, PostTask):
                return child
        return None


    def isInPost(self, bId:str) -> bool:
        pass

    def __split(self) -> None:
        builds = self.__buildSet.getBuilds()

        children = [] # type: List[Task]

        # Build children which type is SingleTask
        for build in builds:
            st = SingleTask(build.getIdent(), sn = self.sn, revision = self.vsn,
                            build = build,
                            extra = self.extra)
            st.setParent(self)
            children.append(st)

        # Build a child which type is PostTask
        allBuilds_ident = list(map(lambda b: b.getIdent(), self.__buildSet.getBuilds()))
        frags = list(filter(lambda bid: self.__buildSet.belongTo(bid) is None, allBuilds_ident))

        posts = self.__buildSet.getPosts()
        merge = self.__buildSet.getMerge()

        pt = PostTask(self.vsn, posts, frags, merge)

        children.append(pt)
        self.__children = children

class SingleTask(Task):

    Type = 1

    def __init__(self, id:str, sn:str, revision:str,
                 build:Build,
                 extra:Dict = {}):

        Task.__init__(self, SingleTask.Type, id, sn, revision, extra)

        self.__build = build
        self.__parent = None # type: Optional[SuperTask]
        self.__postGroup = None # type: Optional[str]

    def setParent(self, parent:SuperTask) -> None:
        self.__parent = parent

    def getParent(self) -> Optional[SuperTask]:
        return self.__parent

    def isAChild(self) -> bool:
        return self.__parent is not None

    def toLetter(self) -> NewLetter:

        build = self.__build
        extra = {"resultPath":build.getOutput(), "cmds":build.getCmd()}

        if self.isAChild():
            parent_ident = self.getParent().id() # type: ignore
            needPost = "true"
            group = self.__parent.getGroupOf(self.id()) # type: ignore
        else:
            parent_id = ""
            needPost = "false"

        menu = ""

        if self.__postGroup is not None:
            menu = self.__postGroup

        return NewLetter(self.id(), self.sn, self.vsn, str(datetime.utcnow()),
                         parent = parent_ident,
                         extra = extra,
                         menu = menu,
                         needPost = needPost)


class PostTask(Task):

    Type = 2

    def __init__(self, version:str, groups:List[Post], frags:List[str], merge:Merge):
        Task.__init__(self, PostTask.Type, version, "", version)

        self.__postGroups = groups
        self.__frags = frags
        self.__merge = merge
        self.__parent = None # type: Optional[SuperTask]

    def setParent(self, parent:SuperTask) -> None:
        self.__parent = parent

    def getParent(self) -> Optional[SuperTask]:
        return self.__parent

    def toLetter(self) -> PostTaskLetter:

        version = self.vsn
        posts = self.__postGroups
        menuLetters = list(map(lambda p: p.toMenuLetter(version), posts))

        postTaskLetter = PostTaskLetter(self.vsn,
                                        self.__merge.getCmds(),
                                        self.__merge.getOutput(),
                                        frags=self.__frags)

        for menuLetter in menuLetters:
            postTaskLetter.addMenu(menuLetter)

        return postTaskLetter



# Every task in TaskGroup must be unique in the TaskGroup
class TaskGroup:
    def __init__(self) -> None:
        # {Type:Tasks}
        self.__tasks = {} # type: Dict[TaskType, Dict[str, Task]]
        self.__numOfTasks = 0
        self.__lock = Lock()

    def newTask(self, task: Task) -> None:
        type = task.getType()
        tid = task.id()

        with self.__lock:

            if self.__isExists(tid):
                return None

            if type not in self.__tasks:
                self.__tasks[type] = {}

            tasks = self.__tasks[type]

            tasks[task.id()] = task
            self.__numOfTasks += 1

    def remove(self, id: str) -> State:

        with self.__lock:
            task_dicts = list(self.__tasks.values())

            for tasks in task_dicts:
                if not id in tasks:
                    continue

                del tasks [id]
                self.__numOfTasks -= 1

                return Ok

            return Error

    def __mark(self, id: str, st: TaskState) -> State:
        task = self.search(id)
        if task is None:
            return Error
        task.stateChange(st)

        return Ok

    def toList(self) -> List[Task]:
        with self.__lock:
            task_dicts = list(self.__tasks.values())
            task_lists = list(map(lambda d: list(d.values()), task_dicts))

            return reduce(lambda acc, cur: acc + cur, task_lists)

    def toList_(self) -> List[str]:
        l = self.toList()
        l_id = map(lambda t: t.id(), l)

        return list(l_id)

    def isExists(self, ident:str) -> bool:
        with self.__lock: return self.__isExists(ident)

    def __isExists(self, ident:str) -> bool:
        task_dicts = list(self.__tasks.values())

        for tasks in task_dicts:
            if not id in tasks:
                continue

            return True

        return False


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
            tasks_dicts = list(self.__tasks.values())

            for tasks in tasks_dicts:
                if id not in tasks:
                    continue

                return tasks[id]

            return None

    def numOfTasks(self) -> int:
        return self.__numOfTasks
