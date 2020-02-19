# build.py

from typing import Dict, List, Union, Optional
from functools import reduce

MAX_LENGTH_OF_COMMAND = 1024

class BUILD_FORMAT_WRONG(Exception):
    pass

class Build:

    def __init__(self, bId:str, build:Dict) -> None:

        if not Build.isValid(build):
            raise BUILD_FORMAT_WRONG

        self.__bId = bId
        self.__cmds = build['cmd']
        self.__cmdStr = ";".join(self.__cmds)
        self.__output = build['output']

    def getIdent(self) -> str:
        return self.__bId

    def getCmd(self) -> List[str]:
        return self.__cmds

    def getCmdStr(self) -> str:
        return self.__cmdStr

    def getOutput(self) ->  str:
        return self.__output

    def length(self) -> int:
        return len(self.__cmdStr)

    @staticmethod
    def isValid(build:Dict) -> bool:
        return 'cmd' in build and 'output' in build

class BuildSet:

    def __init__(self, buildSet:Dict) -> None:

        if not BuildSet.isValid(buildSet):
            raise BUILD_FORMAT_WRONG

        self.__builds = BuildSet.__split(buildSet)
        self.__postBelong = {} # type: Dict[str, List[Build]]
        self.__postBuilds = {} # type: Dict[str, Build]

        self.__buildPosts(buildSet)

    def belongTo(self, bId) -> Optional[List[Build]]:
        if not bId in self.__postBelong:
            return None
        return self.__postBelong[bId]

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
            build = builds_dict[bId]
            build['RepoUrl'] = buildSet['RepoUrl']
            build['ProjectName'] = buildSet['Projectname']

            builds[bId] = Build(bId, builds_dict[bId])

        return builds

    def __buildPosts(self, buildSet:Dict) -> None:
        postGroups = buildSet['Posts']

        # Build a dict to store post and their post build
        for pId in postGroups:
            post = postGroups[pId]
            self.__postBuilds[pId] = Build(pId, {"cmd":post['cmd'], "output":post['output']})

        # Build a dict to store relation among builds.
        for pId in postGroups:
            group = postGroups[pId]['group']

            for bId in group:
                buildsOfGroup = list(map(lambda bId: self.__builds[bId], group))
                self.__postBelong[bId] = buildsOfGroup
