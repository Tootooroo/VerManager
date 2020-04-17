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
        self._mName = mName

    def getName(self) -> str:
        return self._mName

    def begin(self) -> None:
        pass

    def cleanup(self) -> None:
        pass

class ModuleDaemon(Module, Daemon):

    def __init__(self, mName:str) -> None:
        Module.__init__(self, mName)
        Daemon.__init__(self)

ModuleName = str

class MManager:

    def __init__(self):
        self._modules = {} # type: Dict[ModuleName, Module]
        self._num = 0

    def isModuleExists(self, mName:ModuleName) -> bool:
        return mName in self._modules

    def numOfModules(self):
        return self._num

    def getModule(self, mName:ModuleName) -> Optional[Module]:
        if self.isModuleExists(mName):
            return self._modules[mName]

        return None

    def getAllModules(self) -> List[Module]:
        return list(self._modules.values())

    def getAlives(self) -> List[Module]:
        (alives, dies) = partition(self._modules, lambda m: m.is_alive())
        return alives

    def getDies(self) -> List[Module]:
        (alives, dies) = partition(self._modules, lambda m: m.is_alive())
        return dies

    def addModule(self, m:Module) -> State:
        mName = m.getName()

        if self.isModuleExists(mName):
            return Error

        self._modules[mName] = m
        self._num += 1

        return Ok

    def removeModule(self, mName:ModuleName) -> Optional[Module]:
        if self.isModuleExists(mName):
            m = self._modules[mName]

            m.cleanup()
            if isinstance(m, ModuleDaemon):
                m.stop()

            del self._modules [mName]
            self._num -= 1

            return m

        return None

    def start(self, mName) -> None:
        if self.isModuleExists(mName):
            m = self._modules[mName]
            m.start()

    def stop(self, mName) -> None:
        if self.isModuleExists(mName):
            m = self._modules[mName]
            m.stop()

    def startAll(self) -> None:
        allMods = self.getAllModules()

        for mod in allMods:
            mod.begin()
            if isinstance(mod, ModuleDaemon):
                mod.start()

    def stopAll(self) -> None:
        allMods = self.getAllModules()

        for mod in allMods:
            if isinstance(mod, ModuleDaemon):
                mod.stop()

            mod.cleanup()

    def join(self) -> None:
        allMods = self.getAllModules()

        for mod in allMods:
            if isinstance(mod, ModuleDaemon):
                mod.join()
