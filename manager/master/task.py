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

    Type = 0

    # Task does not dispatch to any worker.
    STATE_PREPARE = 0

    # Task was dispatch to a worker.
    STATE_IN_PROC = 1

    # Task is done and the result of task has been received.
    STATE_FINISHED = 2

    # Task is failure.
    STATE_FAILURE = 3

    STATE_TOPOLOGY = {
        STATE_PREPARE:[STATE_PREPARE, STATE_IN_PROC, STATE_FAILURE],
        STATE_IN_PROC:[STATE_IN_PROC, STATE_PREPARE, STATE_FINISHED, STATE_FAILURE],
        STATE_FINISHED:[STATE_FINISHED, STATE_FAILURE],
        STATE_FAILURE:[STATE_FAILURE]
    } # type: Dict[int, List[int]]


    def __init__(self, id: str, sn:str, vsn:str,
                 extra:Dict[str, str] = {}) -> None:

        self.taskId = id

        self.type = Task.Type
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
        self.refs = 1

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

    def stateChange(self, state:int) -> State:
        ableStates = Task.STATE_TOPOLOGY[self.taskState()]

        if state in ableStates:
            self.state = state
            return Ok
        else:
            return Error

    def toPreState(self) -> State:
        self.state = Task.STATE_PREPARE
        return Ok

    def toProcState(self) -> State:
        return self.stateChange(Task.STATE_IN_PROC)

    def toFinState(self) -> State:
        return self.stateChange(Task.STATE_FINISHED)

    def toFailState(self) -> State:
        return self.stateChange(Task.STATE_FAILURE)

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
        return s >= Task.STATE_PREPARE and s <= Task.STATE_FAILURE

    def transform(self) -> 'Task':
        if type(self) is not Task:
            return self

        if isinstance(self.build, Build):
            return SingleTask(self.id(), self.sn, self.vsn, self.build, self.extra)
        elif isinstance(self.build, BuildSet):
            return SuperTask(self.id(), self.sn, self.vsn, self.build)

        raise TASK_TRANSFORM_ERROR

class SuperTask(Task):

    Type = 1

    def __init__(self, id:str, sn:str, revision:str, buildSet:BuildSet) -> None:

        Task.__init__(self, id, sn, revision)

        self.type = SuperTask.Type
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

    def toPreState(self) -> State:
        isAbleTo = True
        for c in self.__children:
            isAbleTo = isAbleTo and c.isPrepare()
        if isAbleTo:
            self.state = Task.STATE_PREPARE
            return Ok

        return Error

    def toFinState(self) -> State:
        isAbleTo = True
        for c in self.__children:
            isAbleTo = c.isFinished()
        if isAbleTo:
            self.state = Task.STATE_FINISHED
            return Ok

        return Error

    def toFailState(self) -> State:
        failedChildren = list(filter(lambda child: child.isFailure(), self.__children))

        if len(failedChildren) > 0:
            self.state = Task.STATE_FAILURE
            return Ok

        return Error

    def toState_force(self, state:TaskState) -> State:
        ret = True

        for c in self.__children:
            c_ret = c.stateChange(state)
            if c_ret is Error:
                ret = ret and False

        if ret is False:
            return Error

        self.state = state

        return Ok


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
        # Generate tasks from SuperTask
        # Version should attach to subtasks's tid
        # and Post group's member's id too.
        builds = self.__buildSet.getBuilds()

        children = [] # type: List[Task]

        # Function to attach version ident to SingleTask's tid.
        prefix = lambda ident: self.id() + "__" + ident

        # fixme: should provide a command object so we can easily to
        #        handle variable in command.
        varPairs = [] # type: List[Tuple[str, str]]
        extra = self.getExtra()

        if extra is not None:
            if "datetime" in extra:
                datetime = extra['datetime']
            else:
                datetime = ""

            version = self.getVSN()

            varPairs = [("<version>", version), ("<datetime>", datetime)]

        # Build children which type is SingleTask
        for build in builds:

            if varPairs != []:
                build.varAssign(varPairs)

            st = SingleTask(prefix(build.getIdent()), sn = self.sn, revision = self.vsn,
                            build = build,
                            extra = self.extra)

            st.setParent(self)

            group = self.__buildSet.belongTo(build.getIdent())
            if group is not None:
                st.setGroup(group[0])

            children.append(st)

        # Build a child which type is PostTask
        allBuilds_ident = list(map(lambda b: b.getIdent(), self.__buildSet.getBuilds()))
        frags = list(filter(lambda bid: self.__buildSet.belongTo(bid) is None, allBuilds_ident))

        # Get posts from BuildSet and attach version to member's id.
        posts = self.__buildSet.getPosts()
        for post in posts:
            if varPairs != []:
                post.varAssign(varPairs)

            cmds = post.getCmds()
            members = post.getMembers()
            members = list(map(lambda member: prefix(member), members))
            post.setMembers(members)

        merge = self.__buildSet.getMerge()
        if varPairs != []:
            merge.varAssign(varPairs)

        pt = PostTask(self.vsn, posts, frags, merge)
        pt.setParent(self)

        children.append(pt)

        self.__children = children

class SingleTask(Task):

    Type = 2

    def __init__(self, id:str, sn:str, revision:str,
                 build:Build,
                 extra:Dict = {}) -> None:

        Task.__init__(self, id, sn, revision, extra)

        self.type = SingleTask.Type
        self.__build = build
        self.__parent = None # type: Optional[SuperTask]
        self.__postGroup = None # type: Optional[str]

    def setParent(self, parent:SuperTask) -> None:
        self.__parent = parent

    def getParent(self) -> Optional[SuperTask]:
        return self.__parent

    def setGroup(self, group:str) -> None:
        self.__postGroup = group

    def getGroup(self) -> Optional[str]:
        return self.__postGroup

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

    def isBindWithBuild(self) -> bool:
        return self.__build is not None


class PostTask(Task):

    Type = 3

    def __init__(self, version:str, groups:List[Post], frags:List[str], merge:Merge) -> None:
        Task.__init__(self, version, "", version)

        self.type = PostTask.Type
        self.__postGroups = groups
        self.__frags = frags
        self.__merge = merge
        self.__parent = None # type: Optional[SuperTask]

    def setParent(self, parent:SuperTask) -> None:
        self.__parent = parent

    def getParent(self) -> Optional[SuperTask]:
        return self.__parent

    def getGroups(self) -> List[Post]:
        return self.__postGroups

    def setGroups(self, groups:List[Post]) -> None:
        self.__postGroups = groups

    def isAChild(self) -> bool:
        return self.__parent is not None

    def toLetter(self) -> PostTaskLetter:

        version = self.vsn
        posts = self.__postGroups
        menuLetters = list(map(lambda p: p.toMenuLetter(version), posts))

        postTaskLetter = PostTaskLetter(self.vsn,
                                        self.__merge.getCmds(),
                                        self.__merge.getOutput(),
                                        frags=self.__frags,
                                        menus = {})
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

            if not isinstance(task, PostTask):
                self.__numOfTasks += 1

    def remove(self, id: str) -> State:
        with self.__lock: return self.__remove(id)

    def __remove(self, id:str) -> State:
        task_dicts = list(self.__tasks.values())

        for tasks in task_dicts:
            if not id in tasks:
                continue

            task = tasks[id]
            del tasks [id]

            if not isinstance(task, PostTask):
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
        with self.__lock: return self.__toList_non_lock()

    def __toList_non_lock(self) -> List[Task]:
        task_dicts = list(self.__tasks.values())
        task_lists = list(map(lambda d: list(d.values()), task_dicts))

        return reduce(lambda acc, cur: acc + cur, task_lists, [])

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

    def removeTasks(self, predicate:Callable[[Task], bool]) -> None:
        with self.__lock:
            for t in self.__toList_non_lock():
                ret = predicate(t)

                if ret is True:
                    self.__remove(t.id())

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
