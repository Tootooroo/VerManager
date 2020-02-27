# info.py

import typing
from typing import Generic, TypeVar
from yaml import load, SafeLoader
from functools import reduce

# Abstruction of configuration file
class Info:

    def __init__(self, cfgPath: str) -> None:
        with open(cfgPath, "r") as f:
            self.__config = load(f, Loader=SafeLoader)


    def getConfig(self, *cfgKeys) -> typing.Any:
        cfgValue = self.__config

        try:
            for i in cfgKeys:
                cfgValue = cfgValue[i]
        except KeyError:
            return ""

        return cfgValue

    # Value of the dict may be a string may be a dict
    def getConfigs(self) -> typing.Dict[str, typing.Any]:
        return self.__config

    def validityChecking(self, predicates) -> bool:
        results = list(map(lambda p: p(self.__config), predicates))
        return reduce(lambda acc, curr: acc and curr, results)
