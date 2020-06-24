# mmanager.py

import unittest
import asyncio

from abc import ABC, abstractmethod
from typing import Optional, List, Dict
from threading import Thread
from .util import partition

from .type import State, Ok, Error


class Daemon(ABC):

    def __init__(self) -> None:
        self.daemon = True
        self.alive = False

    def is_alive(self) -> bool:
        return self.alive

    @abstractmethod
    async def stop(self) -> None:
        """ Method to stop Daemon """

    @abstractmethod
    def needStop(self) -> bool:
        """
        Daemon use this method to confirm whether
        stop is need.
        """

    @abstractmethod
    async def run(self) -> None:
        """ An asyncio method that do jobs """

    async def start(self) -> None:
        await self.run()

class Module(ABC):

    def __init__(self, mName: str) -> None:
        self._mName = mName

    def getName(self) -> str:
        return self._mName

    @abstractmethod
    async def begin(self) -> None:
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        pass


class ModuleDaemon(Module, Daemon):

    def __init__(self, mName: str) -> None:
        Module.__init__(self, mName)
        Daemon.__init__(self)


ModuleName = str


class MManager:

    def __init__(self):
        self._modules = {}  # type: Dict[ModuleName, Module]
        self._num = 0

    def isModuleExists(self, mName: ModuleName) -> bool:
        return mName in self._modules

    def numOfModules(self):
        return self._num

    def getModule(self, mName: ModuleName) -> Optional[Module]:
        if self.isModuleExists(mName):
            return self._modules[mName]

        return None

    def getAllModules(self) -> List[Module]:
        return list(self._modules.values())

    def getAlives(self) -> List[Module]:
        (alives, dies) = partition(list(self._modules.values()),
                                   lambda m: m.is_alive())
        return alives

    def getDies(self) -> List[Module]:
        (alives, dies) = partition(list(self._modules.values()),
                                   lambda m: m.is_alive())
        return dies

    def addModule(self, m: Module) -> State:
        mName = m.getName()

        if self.isModuleExists(mName):
            return Error

        self._modules[mName] = m
        self._num += 1

        return Ok

    async def removeModule(self, mName: ModuleName) -> Optional[Module]:
        if self.isModuleExists(mName):
            m = self._modules[mName]

            await m.cleanup()

            if isinstance(m, ModuleDaemon):
                await m.stop()

            del self._modules[mName]
            self._num -= 1

            return m

        return None

    async def start(self, mName) -> None:
        if self.isModuleExists(mName):
            m = self._modules[mName]
            if isinstance(m, ModuleDaemon):
                await m.start()

    async def stop(self, mName) -> None:
        if self.isModuleExists(mName):
            m = self._modules[mName]
            if isinstance(m, ModuleDaemon):
                await m.stop()

    async def startAll(self) -> None:
        allMods = self.getAllModules()

        for mod in allMods:
            await mod.begin()
            if isinstance(mod, ModuleDaemon):
                await mod.start()

    async def stopAll(self) -> None:
        allMods = self.getAllModules()

        for mod in allMods:
            if isinstance(mod, ModuleDaemon):
                await mod.stop()

            await mod.cleanup()


# TestCases
class MManagerTestCases(unittest.TestCase):

    def test_case(self):

        class ModuleExample(Module):

            def __init__(self, name: str) -> None:
                Module.__init__(self, name)

                self.running = False

            async def begin(self):
                self.running = True

            async def cleanup(self):
                self.running = False

        class DaemonExample(ModuleDaemon):

            def __init__(self, name:str) -> None:
                ModuleDaemon.__init__(self, name)

                self.running = False
                self.done = False
                self.stoped = False

            async def begin(self) -> None:
                self.running = True

            async def cleanup(self) -> None:
                self.running = False

            async def stop(self) ->  None:
                self.stoped = True

            def needStop(self) -> bool:
                return True

            async def run(self) -> None:
                self.done = True

        async def test() -> None:
            manager = MManager()

            m1 = ModuleExample("M1")
            m2 = ModuleExample("M2")

            manager.addModule(m1)
            manager.addModule(m2)

            self.assertTrue(manager.isModuleExists("M1"))
            self.assertTrue(manager.isModuleExists("M2"))

            self.assertTrue(not manager.isModuleExists("M_NOT_EXISTS"))

            await manager.startAll()

            self.assertTrue(m1.running is True)
            self.assertTrue(m2.running is True)

            await manager.stopAll()
            self.assertTrue(m1.running is False)
            self.assertTrue(m2.running is False)

            # Test Daemon
            dm1 = DaemonExample("dm1")
            dm2 = DaemonExample("dm2")
            manager.addModule(dm1)
            manager.addModule(dm2)

            await manager.startAll()
            self.assertTrue(m1.running is True)
            self.assertTrue(m2.running is True)
            self.assertTrue(dm1.running is True and dm1.done is True)
            self.assertTrue(dm2.running is True and dm2.done is True)

            await manager.stopAll()
            self.assertTrue(m1.running is False)
            self.assertTrue(m2.running is False)
            self.assertTrue(dm1.running is False and dm1.stoped is True)
            self.assertTrue(dm2.running is False and dm2.stoped is True)


        asyncio.run(test())
