# MIT License
#
# Copyright (c) 2020 Gcom
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# task.py

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, \
    BinaryIO, Union, Any, Tuple, Callable
from functools import reduce
from manager.basic.type import Ok, Error, State
from manager.basic.letter import NewLetter, Letter, \
    PostTaskLetter, BinaryLetter
from manager.master.build import BuildSet
from manager.basic.restricts import TASK_ID_MAX_LENGTH, VERSION_MAX_LENGTH, \
    REVISION_MAX_LENGTH

from datetime import datetime
from threading import Lock

from manager.master.build import Build, Post, Merge

TaskState = int

TaskType = int


class TASK_FORMAT_ERROR(Exception):
    pass


class TASK_TRANSFORM_ERROR(Exception):
    pass


class TaskBase(ABC):

    @abstractmethod
    def id(self) -> str:
        """ identity of task """

    @abstractmethod
    def dependence(self) -> List['TaskBase']:
        """ Which task dependen to """

    @abstractmethod
    def dependedBy(self) -> List['TaskBase']:
        """ Return a liste of tasks that depend on this task  """

    @abstractmethod
    def taskState(self) -> TaskState:
        """ State of Task """

    @abstractmethod
    def stateChange(self, state: TaskState) -> State:
        """ Change task's state """

    @abstractmethod
    def isValid(self) -> bool:
        """ To check that is info in this task is valid  """


class Task(TaskBase):

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
        STATE_PREPARE: [STATE_PREPARE, STATE_IN_PROC, STATE_FAILURE],
        STATE_IN_PROC: [STATE_IN_PROC, STATE_PREPARE,
                        STATE_FINISHED, STATE_FAILURE],
        STATE_FINISHED: [STATE_PREPARE, STATE_FINISHED, STATE_FAILURE],
        STATE_FAILURE: [STATE_FAILURE]
    }  # type:  Dict[int, List[int]]

    def __init__(self, id:  str, sn: str, vsn: str,
                 extra: Dict[str, str] = {}) -> None:

        self.taskId = id

        self.type = Task.Type
        self.sn = sn
        self.vsn = vsn
        self.extra = extra

        # Files that relate to this task
        self._files = None  # type:  Optional[BinaryIO]

        self.state = Task.STATE_PREPARE

        # This field will be set by EventListener while
        # the task is complete by worker and transfer
        # back totally.
        self.data = ""

        self.build = None  # type:  Optional[Union[Build, BuildSet]]

        # Indicate that the number of request to the task
        self.refs = 1

        self.lastAccess = datetime.utcnow()

    def getType(self) -> TaskType:
        return self.type

    def setType(self, type: TaskType) -> None:
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

    def setBuild(self, b: Union[Build, BuildSet]) -> None:
        self.build = b

    def isBindWithBuild(self) -> bool:
        return self.build is not None

    def stateChange(self, state: int) -> State:
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

    def setData(self, data:  str) -> None:
        self.data = data

    def isPrepare(self) -> bool:
        return self.state == Task.STATE_PREPARE

    def isProc(self) -> bool:
        return self.state == Task.STATE_IN_PROC

    def isFailure(self) -> bool:
        return self.state == Task.STATE_FAILURE

    def isFinished(self) -> bool:
        return self.state == Task.STATE_FINISHED

    def dependence(self) -> List['TaskBase']:
        return []

    def dependedBy(self) -> List['TaskBase']:
        return []

    # fixme:  Python 3.5.3 raise an NameError exception:
    #        name 'BinaryIO' is not defined. Temporarily
    #        use Any to instead of BinaryIO
    def file(self) -> Optional[Any]:
        return self._files

    def toLetter(self) -> Letter:
        pass

    @staticmethod
    def isValidState(s: int) -> bool:
        return s >= Task.STATE_PREPARE and s <= Task.STATE_FAILURE

    def isValid(self) -> bool:
        cond1 = len(self.taskId) <= TASK_ID_MAX_LENGTH
        cond2 = len(self.vsn) <= VERSION_MAX_LENGTH
        cond3 = len(self.sn) <= REVISION_MAX_LENGTH
        cond4 = " " not in (self.taskId+self.vsn+self.sn)

        return cond1 and cond2 and cond3 and cond4

    def transform(self) -> 'Task':
        if type(self) is not Task:
            return self

        if isinstance(self.build, Build):
            return SingleTask(self.id(), self.sn, self.vsn,
                              self.build, self.extra)
        elif isinstance(self.build, BuildSet):
            return SuperTask(self.id(), self.sn, self.vsn,
                             self.build, self.extra)

        raise TASK_TRANSFORM_ERROR


class SuperTask(Task):

    Type = 1

    def __init__(self, id: str, sn: str, revision: str,
                 buildSet: BuildSet, extra: Dict) -> None:

        Task.__init__(self, id, sn, revision, extra)

        self.type = SuperTask.Type
        self._children = []  # type:  List['Task']
        self._buildSet = buildSet

        self._split()

    def dependence(self) -> List[TaskBase]:
        return [c for c in self._children]

    def dependedBy(self) -> List[TaskBase]:
        return []

    def getChildren(self) -> List[Task]:
        return self._children

    def getChild(self, ident: str) -> Optional[Task]:
        maybe_the_child = list(filter(lambda w:  w.id() == ident,
                                      self._children))

        count = len(maybe_the_child)
        if count == 1:
            return maybe_the_child[0]

        return None

    def getGroupOf(self, tid: str) -> Optional[List[Task]]:
        group = []  # type:  List[Task]

        builds = self._buildSet.belongTo(tid)
        if builds is None:
            return None

        builds_list = builds[1]

        for b in builds_list:
            ident = self.getVSN() + "__" + b.getIdent()
            child = self.getChild(ident)

            if child is None:
                return None

            group.append(child)

        return group

    # For SuperTask isBindWithBuild should always return True
    def isBindWithBuild(self) -> bool:
        return self._buildSet is not None

    def toPreState(self) -> State:
        isAbleTo = False
        for c in self._children:
            isAbleTo = isAbleTo or c.isPrepare()
        if isAbleTo:
            self.state = Task.STATE_PREPARE
            return Ok

        return Error

    def toFinState(self) -> State:
        isAbleTo = True
        for c in self._children:
            isAbleTo = isAbleTo and c.isFinished()
        if isAbleTo:
            self.state = Task.STATE_FINISHED
            return Ok

        return Error

    def toFailState(self) -> State:
        failedChildren = list(filter(lambda child:  child.isFailure(),
                                     self._children))

        if len(failedChildren) > 0:
            self.state = Task.STATE_FAILURE
            return Ok

        return Error

    def toState_force(self, state: TaskState) -> State:
        ret = True

        for c in self._children:
            c_ret = c.stateChange(state)
            if c_ret is Error:
                ret = ret and False

        if ret is False:
            return Error

        self.state = state

        return Ok

    def setBuildSet(self, buildSet: BuildSet) -> None:
        self._buildSet = buildSet

    def getPostTask(self) -> Optional['PostTask']:
        for child in self._children:
            if isinstance(child, PostTask):
                return child
        return None

    def isInPost(self, bId: str) -> bool:
        pass

    def _split(self) -> None:
        # Generate tasks from SuperTask
        # Version should attach to subtasks's tid
        # and Post group's member's id too.
        builds = self._buildSet.getBuilds()

        children = []  # type:  List[Task]

        # Function to attach version ident to SingleTask's tid.
        prefix = lambda ident:  self.id() + "__" + ident

        # fixme:  should provide a command object so we can easily to
        #        handle variable in command.
        varPairs = []  # type:  List[Tuple[str, str]]
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

            st = SingleTask(prefix(build.getIdent()), sn=self.sn,
                            revision=self.vsn,
                            build=build,
                            extra=self.extra)

            if st.isValid() is False:
                raise TASK_FORMAT_ERROR

            st.setParent(self)

            group = self._buildSet.belongTo(build.getIdent())
            if group is not None:
                st.setGroup(group[0])

            children.append(st)

        # Build frags
        allBuilds_ident = list(map(lambda b:  b.getIdent(),
                                   self._buildSet.getBuilds()))
        predicate = lambda ident:  self._buildSet.belongTo(ident) is None
        frags = [prefix(ident) for ident in allBuilds_ident
                 if predicate(ident)]

        # Get posts from BuildSet and attach version to member's id.
        posts = self._buildSet.getPosts()
        for post in posts:
            if varPairs != []:
                post.varAssign(varPairs)

            members = post.getMembers()
            members = list(map(lambda member:  prefix(member), members))
            post.setMembers(members)

        merge = self._buildSet.getMerge()
        if varPairs != []:
            merge.varAssign(varPairs)

        pt = PostTask(PostTask.genIdent(self.vsn),
                      self.vsn, posts, frags, merge)

        if pt.isValid() is False:
            raise TASK_FORMAT_ERROR

        pt.setParent(self)

        children.append(pt)

        self._children = children


class SingleTask(Task):

    Type = 2

    def __init__(self, id: str, sn: str, revision: str,
                 build: Build,
                 extra: Dict = {}) -> None:

        Task.__init__(self, id, sn, revision, extra)

        self.type = SingleTask.Type
        self._build = build
        self._parent = None  # type:  Optional[SuperTask]
        self._postGroup = None  # type:  Optional[str]

    def setParent(self, parent: SuperTask) -> None:
        self._parent = parent

    def getParent(self) -> Optional[SuperTask]:
        return self._parent

    def setGroup(self, group: str) -> None:
        self._postGroup = group

    def getGroup(self) -> Optional[str]:
        return self._postGroup

    def isAChild(self) -> bool:
        return self._parent is not None

    def isValid(self) -> bool:
        cond1 = len(self.taskId) <= BinaryLetter.TASK_ID_FIELD_LEN
        cond2 = len(self.vsn) <= VERSION_MAX_LENGTH
        cond3 = len(self.sn) <= REVISION_MAX_LENGTH
        cond4 = " " not in (self.taskId+self.vsn+self.sn)

        return cond1 and cond2 and cond3 and cond4

    def denpendence(self) -> List['TaskBase']:
        return []

    def dependedBy(self) -> List['TaskBase']:
        if self._parent is not None:
            post = self._parent.getPostTask()
            if post is not None:
                return [self._parent, post]

        return []

    def toLetter(self) -> NewLetter:

        build = self._build
        extra = {"resultPath": build.getOutput(), "cmds": build.getCmd()}

        if self.isAChild():
            parent_ident = self.getParent().id()  # type:  ignore
            needPost = "true"
        else:
            parent_ident = ""
            needPost = "false"

        menu = ""

        if self._postGroup is not None:
            menu = self._postGroup

        return NewLetter(self.id(), self.sn, self.vsn, str(datetime.utcnow()),
                         parent=parent_ident,
                         extra=extra,
                         menu=menu,
                         needPost=needPost)

    def isBindWithBuild(self) -> bool:
        return self._build is not None


class PostTask(Task):

    Type = 3

    def __init__(self, ident: str, version: str,
                 groups: List[Post], frags: List[str], merge: Merge) -> None:

        Task.__init__(self, ident, "", version)

        self.type = PostTask.Type
        self._postGroups = groups
        self._frags = frags
        self._merge = merge
        self._parent = None  # type:  Optional[SuperTask]

    @staticmethod
    def genIdent(ident: str) -> str:
        return ident+"__Post"

    def setParent(self, parent: SuperTask) -> None:
        self._parent = parent

    def getParent(self) -> Optional[SuperTask]:
        return self._parent

    def getGroups(self) -> List[Post]:
        return self._postGroups

    def setGroups(self, groups: List[Post]) -> None:
        self._postGroups = groups

    def isAChild(self) -> bool:
        return self._parent is not None

    def isValid(self) -> bool:
        cond1 = len(self.taskId) <= BinaryLetter.TASK_ID_FIELD_LEN
        cond2 = len(self.vsn) <= VERSION_MAX_LENGTH
        cond3 = len(self.sn) <= REVISION_MAX_LENGTH
        cond4 = " " not in (self.taskId+self.vsn+self.sn)

        return cond1 and cond2 and cond3 and cond4

    def dependence(self) -> List[TaskBase]:
        if self._parent is None:
            return []

        children = self._parent.getChildren()
        return [child for child in children if child is not self]

    def dependedBy(self) -> List[TaskBase]:
        if self._parent is not None:
            return [self._parent]

        return []

    def toLetter(self) -> PostTaskLetter:

        version = self.vsn
        posts = self._postGroups
        menuLetters = list(map(lambda p:  p.toMenuLetter(version), posts))

        postTaskLetter = PostTaskLetter(self.vsn+"__Post",
                                        self.vsn,
                                        self._merge.getCmds(),
                                        self._merge.getOutput(),
                                        frags=self._frags,
                                        menus={})
        for menuLetter in menuLetters:
            postTaskLetter.addMenu(menuLetter)

        return postTaskLetter


# Every task in TaskGroup must be unique in the TaskGroup
class TaskGroup:
    def __init__(self) -> None:
        # {Type: Tasks}
        self._tasks = {}  # type:  Dict[TaskType, Dict[str, Task]]
        self._numOfTasks = 0
        self._lock = Lock()

    def newTask(self, task:  Task) -> None:
        type = task.getType()
        tid = task.id()

        with self._lock:

            if self.__isExists(tid):
                return None

            if type not in self._tasks:
                self._tasks[type] = {}

            tasks = self._tasks[type]

            tasks[task.id()] = task

            if not isinstance(task, PostTask):
                self._numOfTasks += 1

    def remove(self, id:  str) -> State:
        with self._lock:
            return self.__remove(id)

    def __remove(self, id: str) -> State:
        for tasks in self._tasks.values():

            if id not in tasks:
                continue

            task = tasks[id]
            del tasks[id]

            if not isinstance(task, PostTask):
                self._numOfTasks -= 1

            return Ok

        return Error

    def _mark(self, id:  str, st:  TaskState) -> State:
        task = self.search(id)
        if task is None:
            return Error
        task.stateChange(st)

        return Ok

    def toList(self) -> List[Task]:
        with self._lock:
            return self._toList_non_lock()

    def _toList_non_lock(self) -> List[Task]:
        task_dicts = list(self._tasks.values())
        task_lists = list(map(lambda d:  list(d.values()), task_dicts))

        return reduce(lambda acc, cur:  acc + cur, task_lists, [])

    def toList_(self) -> List[str]:
        letter = self.toList()
        l_id = map(lambda t:  t.id(), letter)

        return list(l_id)

    def isExists(self, ident: str) -> bool:
        with self._lock:
            return self.__isExists(ident)

    def __isExists(self, ident: str) -> bool:
        task_dicts = list(self._tasks.values())

        for tasks in task_dicts:
            if id not in tasks:
                continue

            return True

        return False

    def removeTasks(self, predicate: Callable[[Task], bool]) -> None:
        with self._lock:
            for t in self._toList_non_lock():
                ret = predicate(t)

                if ret is True:
                    self.__remove(t.id())

    def markPre(self, id:  str) -> State:
        return self._mark(id, Task.STATE_PREPARE)

    def markInProc(self, id: str) -> State:
        return self._mark(id, Task.STATE_IN_PROC)

    def markFin(self, id:  str) -> State:
        return self._mark(id, Task.STATE_FINISHED)

    def markFail(self, id:  str) -> State:
        return self._mark(id, Task.STATE_FAILURE)

    def search(self, id:  str) -> Union[Task, None]:
        with self._lock:
            tasks_dicts = list(self._tasks.values())

            for tasks in tasks_dicts:
                if id not in tasks:
                    continue

                return tasks[id]

            return None

    def numOfTasks(self) -> int:
        return self._numOfTasks


# TestCases
import unittest

class TaskTestCases(unittest.TestCase):

    def test_task(self):
        from manager.basic.info import Info
        from manager.master.build import Build, BuildSet
        from manager.master.task import Task, SuperTask, SingleTask, PostTask
        from manager.basic.letter import MenuLetter

        info = Info("./config_test.yaml")

        buildSet = info.getConfig('BuildSet')

        bs = BuildSet(buildSet)

        # Create a taks object
        t = SuperTask("VersionToto", "ABC", "VersionToto", bs, {})

        # Get a group which GL5610 reside in
        groupOfGL5610 = t.getGroupOf("GL5610")

        # GL5610-v2 should in this group
        GL5610_v2 = list(filter(lambda t: t.id() == "VersionToto__GL5610-v2", groupOfGL5610))
        self.assertTrue(len(GL5610_v2) == 1)
        # Check the parent of GL5610-v2
        self.assertTrue(GL5610_v2[0].isAChild() and GL5610_v2[0].getParent().id() == "VersionToto")

        # GL5610-v3 should in this group too
        GL5610_v3 = list(filter(lambda t: t.id() == "VersionToto__GL5610-v3", groupOfGL5610))
        self.assertTrue(len(GL5610_v3) == 1)
        # Check the parent of GL5610-v3
        self.assertTrue(GL5610_v3[0].isAChild() and GL5610_v3[0].getParent().id() == "VersionToto")

        # Get group which GL8900 reside in
        groupOfGL8900 = t.getGroupOf("GL8900")
        self.assertTrue(len(groupOfGL8900) == 1)
        # Check the parent of GL8900
        self.assertTrue(groupOfGL8900[0].id() == "VersionToto__GL8900",
                        groupOfGL8900[0].getParent().id() == "VersionToto")

        # Posts
        pt = t.getPostTask()
        pt_ident = PostTask.genIdent("VersionToto")
        self.assertEqual(pt_ident, pt.id())
        postLetter = pt.toLetter()

        deps = [t.id() for t in pt.dependence()]
        deps_ = ["VersionToto__GL5610-v2", "VersionToto__GL5610-v3",
                 "VersionToto__GL5610", "VersionToto__GL8900"]
        self.assertEqual(4, len(deps))
        self.assertEqual(deps_.sort(), deps.sort())

        self.assertEqual([], postLetter.frags())
        menus = postLetter.menus()
        self.assertTrue("P1" in menus)
        self.assertTrue("P2" in menus)

        # Menu GL5610 check
        menu_GL5610 = postLetter.getMenu("P1")
        depends = menu_GL5610.getDepends()
        self.assertTrue("VersionToto__GL5610" in depends)
        self.assertTrue("VersionToto__GL5610-v2" in depends)
        self.assertTrue("VersionToto__GL5610-v3" in depends)

        cmds = menu_GL5610.getCmds()
        self.assertEqual(["cat ll ll2 ll3 VersionToto  > post"], cmds)

        # Menu GL8900 check
        menu_GL8900 = postLetter.getMenu("P2")
        depends_89 = menu_GL8900.getDepends()
        self.assertTrue("VersionToto__GL8900" in depends_89)

        cmds = menu_GL8900.getCmds()
        self.assertEqual(["cat ll4 VersionToto  > post_gl8900", "echo 8900 VersionToto  >> post_gl8900"], cmds)

        # Get children of the task
        children = [child.id() for child in t.getChildren()]

        # Check memebers
        self.assertTrue("VersionToto__GL5610" in children)
        self.assertTrue("VersionToto__GL5610-v2" in children)
        self.assertTrue("VersionToto__GL5610-v3" in children)
        self.assertTrue("VersionToto__GL8900" in children)

        # Convert child to letter
        # Format
        # header  : '{"ident":"...", "tid":"...", "needPost":"true/false"}'
        # content : '{"sn":"...", "vsn":"...", "datetime":"...",
        #             "extra":{"resultPath":"...", "cmds":"..."} }"
        v2Letter = GL5610_v2[0].toLetter()

        v2Tid = v2Letter.getHeader("tid")
        self.assertEqual("VersionToto__GL5610-v2", v2Tid)

        v2NeedPost = v2Letter.getHeader("needPost")
        self.assertEqual("true", v2NeedPost)

        v2SN = v2Letter.getContent("sn")
        self.assertEqual("ABC", v2SN)

        v2VSN = v2Letter.getContent("vsn")
        self.assertEqual("VersionToto", v2VSN)

        extra = v2Letter.getContent("extra")

        resultPath = extra['resultPath']
        cmds = extra['cmds']

        self.assertEqual("./ll2", resultPath)
        self.assertEqual(['echo ll2 VersionToto  > ll2'], cmds)
