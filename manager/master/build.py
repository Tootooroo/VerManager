# build.py

from typing import Dict, List, Union, Optional, Tuple
from functools import reduce

from manager.basic.letter import MenuLetter

MAX_LENGTH_OF_COMMAND = 1024

class BUILD_FORMAT_WRONG(Exception):
    pass

class Build:

    def __init__(self, bId:str, build:Dict) -> None:

        if not Build.isValid(build):
            raise BUILD_FORMAT_WRONG

        self.__bId = bId
        self.__cmds = build['cmd']
        self.__output = build['output']

    def getIdent(self) -> str:
        return self.__bId

    def getCmd(self) -> List[str]:
        return self.__cmds

    def getCmdStr(self) -> str:
        return str(self.__cmds).replace("'", "\"")

    def getOutput(self) ->  str:
        return self.__output[0]

    def length(self) -> int:
        return len(self.__cmds)

    @staticmethod
    def isValid(build:Dict) -> bool:
        return 'cmd' in build and 'output' in build

class Post:

    def __init__(self, version:str, ident:str, members:List[str], build:Build) -> None:
        self.__version = version
        self.__ident = ident
        self.__build = build
        self.__members = members

    def getIdent(self) -> str:
        return self.__ident

    def getVersion(self) -> str:
        return self.__version

    def setVersion(self, ver:str) -> None:
        self.__version = ver

    def getMembers(self) -> List[str]:
        return self.__members

    def getBuild(self) -> Build:
        return self.__build

    def toMenuLetter(self) -> MenuLetter:
        cmds = self.__build.getCmd()
        output = self.__build.getOutput()
        mLetter = MenuLetter(self.__version, self.__ident, cmds,
                             self.__members, output)

        return mLetter


class BuildSet:

    def __init__(self, buildSet:Dict) -> None:
        if not BuildSet.isValid(buildSet):
            raise BUILD_FORMAT_WRONG

        self.__builds = BuildSet.__split(buildSet)
        self.__postBelong = {} # type: Dict[str, Tuple[str, List[Build]]]
        self.__posts = {} # type: Dict[str, Post]

        self.__buildPosts(buildSet)

    def belongTo(self, bId) -> Optional[Tuple[str, List[Build]]]:
        if not bId in self.__postBelong:
            return None
        return self.__postBelong[bId]

    def getPosts(self) -> List[Post]:
        return list(self.__posts.values())

    def getBuilds(self) -> List[Build]:
        return list(self.__builds.values())

    def getBuild(self, bId:str) -> Optional[Build]:
        if not bId in self.__builds:
            return None
        return self.__builds[bId]

    def numOfBuilds(self) -> int:
        return len(self.__builds)

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
    def __split(buildSet:Dict) -> Dict[str, Build]:
        builds = {} # type: Dict[str, Build]
        builds_dict = buildSet['Builds']

        for bId in builds_dict:
            builds[bId] = Build(bId, builds_dict[bId])

        return builds

    def __buildPosts(self, buildSet:Dict) -> None:
        postGroups = buildSet['Posts']

        # Build a dict to store post and their post build
        for pId in postGroups:
            post = postGroups[pId]

            build = Build(pId, {"cmd":post['cmd'], "output":post['output']})
            self.__posts[pId] = Post("", pId, post['group'], build)

        # Build a dict to store relation among builds.
        for pId in postGroups:
            group = postGroups[pId]['group']

            for bId in group:
                buildsOfGroup = list(map(lambda bId: self.__builds[bId], group))
                self.__postBelong[bId] = (pId, buildsOfGroup)
