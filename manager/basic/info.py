# info.py

import typing
from typing import Generic, TypeVar
from yaml import load, SafeLoader
from functools import reduce

from manager.basic.mmanager import Module

M_NAME = "Info"

# Abstruction of configuration file
class Info(Module):

    def __init__(self, cfgPath: str) -> None:
        global M_NAME

        Module.__init__(self, M_NAME)
        with open(cfgPath, "r") as f:
            self._config = load(f, Loader=SafeLoader)


    def getConfig(self, *cfgKeys) -> typing.Any:
        cfgValue = self._config

        try:
            for i in cfgKeys:
                cfgValue = cfgValue[i]
        except KeyError:
            return ""

        return cfgValue

    # Value of the dict may be a string may be a dict
    def getConfigs(self) -> typing.Dict[str, typing.Any]:
        return self._config

    def validityChecking(self, predicates) -> bool:
        results = list(map(lambda p: p(self._config), predicates))
        return reduce(lambda acc, curr: acc and curr, results)
