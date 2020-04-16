# build.py

from typing import Dict, List, Union, Optional, Tuple
from functools import reduce

from manager.basic.letter import MenuLetter, PostTaskLetter

MAX_LENGTH_OF_COMMAND = 1024

class BUILD_FORMAT_WRONG(Exception):
    pass

class Build:

    def __init__(self, bId:str, build:Dict) -> None:

        if not Build.isValid(build):
            raise BUILD_FORMAT_WRONG

        self._bId = bId
        self._cmds = build['cmd']
        self._output = build['output']

    def getIdent(self) -> str:
        return self._bId

    def getCmd(self) -> List[str]:
        return self._cmds

    def setCmd(self, cmds:List[str]) -> None:
        self._cmds = cmds

    def getCmdStr(self) -> str:
        return str(self._cmds).replace("'", "\"")

    def getOutput(self) ->  str:
        return self._output[0]

    def length(self) -> int:
        return len(self._cmds)

    @staticmethod
    def isValid(build:Dict) -> bool:
        return 'cmd' in build and 'output' in build

    def varAssign(self, varPairs:List[Tuple[str, str]]) -> None:
        f = lambda cmd, var: cmd.replace(var[0], var[1])
        self._cmds = [reduce(f, varPairs, cmd) for cmd in self._cmds]
        self._output = [reduce(f, varPairs, output) for output in self._output]

class Post:

    def __init__(self, ident:str, members:List[str], build:Build) -> None:
        self._ident = ident
        self._build = build
        self._members = members

    def getIdent(self) -> str:
        return self._ident

    def getMembers(self) -> List[str]:
        return self._members

    def setMembers(self, members:List[str]) -> None:
        self._members = members

    def getBuild(self) -> Build:
        return self._build

    def getCmds(self) -> List[str]:
        return self._build.getCmd()

    def varAssign(self, varPairs:List[Tuple[str, str]]) -> None:
        self._build.varAssign(varPairs)

    def setCmds(self, cmds:List[str]) -> None:
        self._build.setCmd(cmds)

    def toMenuLetter(self, version:str) -> MenuLetter:
        cmds = self._build.getCmd()
        output = self._build.getOutput()
        mLetter = MenuLetter(version, self._ident, cmds,
                             self._members, output)

        return mLetter

class Merge:

    def __init__(self, build:Build) -> None:
        self._build = build

    def getCmds(self) -> List[str]:
        return self._build.getCmd()

    def setCmds(self, cmds:List[str]) -> None:
        self._build.setCmd(cmds)

    def varAssign(self, varPairs:List[Tuple[str, str]]) -> None:
        self._build.varAssign(varPairs)

    def getOutput(self) -> str:
        return self._build.getOutput()


class BuildSet:

    def __init__(self, buildSet:Dict) -> None:
        if not BuildSet.isValid(buildSet):
            raise BUILD_FORMAT_WRONG

        self._builds = BuildSet._split(buildSet)
        self._postBelong = {} # type: Dict[str, Tuple[str, List[Build]]]
        self._posts = {} # type: Dict[str, Post]

        merge = buildSet['Merge']
        mergeBuild = Build("merge", {"cmd":merge['cmd'], "output":merge['output']})
        self._merge = Merge(mergeBuild)

        self._buildPosts(buildSet)

    def belongTo(self, bId) -> Optional[Tuple[str, List[Build]]]:
        if not bId in self._postBelong:
            return None
        return self._postBelong[bId]

    def getMerge(self) -> Merge:
        return self._merge

    def getPosts(self) -> List[Post]:
        return list(self._posts.values())

    def getBuilds(self) -> List[Build]:
        return list(self._builds.values())

    def getBuild(self, bId:str) -> Optional[Build]:
        if not bId in self._builds:
            return None
        return self._builds[bId]

    def numOfBuilds(self) -> int:
        return len(self._builds)

    # fixme: Should also to check relation of builds and posts
    @staticmethod
    def isValid(buildSet:Dict) -> bool:

        # First, to check the valid of builds of buildSet
        if not 'Builds' in buildSet:
            return False

        builds = buildSet['Builds']
        if not isinstance(builds, dict):
            return False

        values = list(builds.values())
        isBuildsValid = not False in list(map(lambda build: Build.isValid(build), values))

        if not isBuildsValid:
            return False

        # Then to check the valid of post of buildSet if exists
        if not 'Posts' in buildSet:
            return True

        posts = list(buildSet['Posts'].values())
        postCheck = lambda post: 'group' in post and 'cmd' in post and 'output' in post
        isPostsValid = not False in list(map(postCheck, posts))

        return isPostsValid

    @staticmethod
    def _split(buildSet:Dict) -> Dict[str, Build]:
        builds = {} # type: Dict[str, Build]
        builds_dict = buildSet['Builds']

        for bId in builds_dict:
            builds[bId] = Build(bId, builds_dict[bId])

        return builds

    def _buildPosts(self, buildSet:Dict) -> None:
        postGroups = buildSet['Posts']

        # Build a dict to store post and their post build
        for pId in postGroups:
            post = postGroups[pId]

            build = Build(pId, {"cmd":post['cmd'], "output":post['output']})
            self._posts[pId] = Post(pId, post['group'], build)

        # Build a dict to store relation among builds.
        for pId in postGroups:
            group = postGroups[pId]['group']

            for bId in group:
                buildsOfGroup = list(map(lambda bId: self._builds[bId], group))
                self._postBelong[bId] = (pId, buildsOfGroup)
