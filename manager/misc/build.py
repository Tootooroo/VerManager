# build.py

import typing
from functools import reduce

MAX_LENGTH_OF_COMMAND = 1024

class BUILD_FORMAT_WRONG(Exception):
    pass

class Build:

    def __init__(self, build:typing.Dict) -> None:

        if not Build.isValid(build):
            raise BUILD_FORMAT_WRONG

        self.__cmds = build['cmd']
        self.__output = build['output']

        self.__cmdStr = reduce(lambda compact, cmd: compact + " && " + cmd, build)

    def getCmd(self) -> typing.List[str]:
        return self.__cmds

    def compactCmd(self) -> str:
        return self.__cmdStr

    def length(self) -> int:
        return len(self.__cmdStr)

    @staticmethod
    def isValid(build:typing.Dict) -> bool:
        return 'cmd' in build and 'output' in build

class BuildSet:

    def __init__(self, buildSet:typing.Dict) -> None:

        if not BuildSet.isValid(buildSet):
            raise BUILD_FORMAT_WRONG

        self.__buildSet = buildSet
        self.__builds = BuildSet.__split(buildSet)

    def getBuild(self, buildName:str) -> Build:
        return self.__builds[buildName]

    def numOfBuilds(self) -> int:
        return len(self.__builds)

    @staticmethod
    def isValid(buildSet:typing.Dict) -> bool:
        values = list(buildSet.values())
        return reduce(lambda acc, build: Build.isValid(acc) and Build.isValid(build), values)

    @staticmethod
    def __split(buildSet:typing.Dict) -> typing.Dict[str, Build]:
        builds = {} # type: typing.Dict[str, Build]

        for build in buildSet:
            builds[build] = buildSet[build]

        return builds
