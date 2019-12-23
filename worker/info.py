# info.py

import typing
from yaml import load, SafeLoader

# Abstruction of configuration file
class Info:

    def __init__(self, cfgPath):
        with open(cfgPath, "r") as f:
            self.__config = load(f, Loader=SafeLoader)


    def getConfig(self, *cfgKeys):
        cfgValue = self.__config

        try:
            for i in cfgKeys:
                cfgValue = cfgValue[i]
        except KeyError:
            return None

        return cfgValue

    def getConfigs(self):
        return self.__config

    def validityChecking(self):
        condition = 'WORKER_NAME' in self.__config and\
                    'REPO_URL' in self.__config and\
                    'PROJECT_NAME' in self.__config

        return condition
