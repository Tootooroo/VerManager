# info.py

import typing
from typing import Generic, TypeVar
from yaml import load, SafeLoader

# Abstruction of configuration file
class Info:

    def __init__(self, cfgPath: str) -> None:
        with open(cfgPath, "r") as f:
            self.__config = load(f, Loader=SafeLoader)


    def getConfig(self, *cfgKeys) -> str:
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

    def validityChecking(self):
        condition = 'WORKER_NAME' in self.__config and\
                    'REPO_URL' in self.__config and\
                    'PROJECT_NAME' in self.__config

        return condition
