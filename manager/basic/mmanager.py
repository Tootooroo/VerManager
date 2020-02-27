# mmanager.py

from typing import Callable, Optional, List
from threading import Thread, Event
from .util import partition

from .type import *

class Daemon(Thread):

    def __init__(self) -> None:
        Thread.__init__(self)
        self.daemon = True


    def stop(self) -> None:
        raise Exception

    def needStop(self) -> bool:
        raise Exception

class Module:

    def __init__(self, mName:str) -> None:
        self.__mName = mName

    def getName(self) -> str:
        return self.__mName

class ModuleDaemon(Module, Daemon):

    def __init__(self, mName:str) -> None:
        Module.__init__(self, mName)
        Daemon.__init__(self)

ModuleName = str

class MManager:

    def __init__(self):
        self.__modules = {} # type: Dict[ModuleName, Module]
        self.__num = 0

    def isModuleExists(self, mName:ModuleName) -> bool:
        return mName in self.__modules

    def numOfModules(self):
        return self.__num

    def getModule(self, mName:ModuleName) -> Optional[Module]:
        if self.isModuleExists(mName):
            return self.__modules[mName]

        return None

    def getAllModules(self) -> List[Module]:
        return list(self.__modules.values())

    def getAlives(self) -> List[Module]:
        (alives, dies) = partition(self.__modules, lambda m: m.is_alive())
        return alives

    def getDies(self) -> List[Module]:
        (alives, dies) = partition(self.__modules, lambda m: m.is_alive())
        return dies

    def addModule(self, mName:ModuleName, m:Module) -> State:
        if self.isModuleExists(mName):
            return Error

        self.__modules[mName] = m
        self.__num += 1

        return Ok

    def removeModule(self, mName:ModuleName) -> Optional[Module]:
        if self.isModuleExists(mName):
            m = self.__modules[mName]
            del self.__modules [mName]
            self.__num -= 1

            return m

        return None

    def start(self, mName) -> None:
        if self.isModuleExists(mName):
            m = self.__modules[mName]
            m.start()

    def stop(self, mName) -> None:
        if self.isModuleExists(mName):
            m = self.__modules[mName]
            m.stop()

    def startAll(self) -> None:
        allMods = self.getAllModules()

        for mod in allMods:
            if isinstance(mod, ModuleDaemon):
                mod.start()

    def stopAll(self) -> None:
        allMods = self.getAllModules()

        for mod in allMods:
            if isinstance(mod, ModuleDaemon):
                mod.stop()
