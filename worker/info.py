# info.py

import typing
from yaml import load, SafeLoader

# Abstruction of configuration file
class Info:

    def __init__(self, cfgPath):
        self.__config = load(cfgPath, Loader=SafeLoader)

    def getConfig(self, *cfgKeys):
        cfgValue = self.__config

        try:
            for i in cfgKeys:
                cfgValue = cfgValue[i]
        except KeyError:
            return None

        return configValue

    def validityChecking(self):
        condition = 'WORKER_NAME' in self.__config and\
                    'REPO_URL' in self.__config and\
                    'PROJECT_NAME' in self.__config

        return condition
