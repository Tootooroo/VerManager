# Storage

import typing

from manager.misc.basic.type import *

from manager.misc.util import pathStrConcate

class STORAGE_IDENT_NOT_FOUND(Exception):
    pass

class StoChooser:

    def __init__(self, path:str) -> None:

        self.__path = path

        try:
            self.__fd = open(path, "wb")
        except FileNotFoundError:
            raise STORAGE_IDENT_NOT_FOUND

    def fd(self) -> typing.BinaryIO:
        return self.__fd

    def setFd(self, fd) -> State:
        self.__fd = fd

        return Ok

    def path(self) -> str:
        return self.__path

    def isValid(self) -> bool:

        try:
            fd = self.__fd
        except:
            return False

        return True

    def store(self, content:bytes) -> None:

        fd = self.__fd

        fd.write(content)

    def retrive(self, count:int) -> bytes:

        fd = self.__fd

        content = fd.read(count)

        return content

    def close(self) -> State:
        fd = self.__fd
        fd.close()

        return Ok


class Storage:

    def __init__(self, path:str, inst:typing.Any) -> None:

        import os

        self.__sInst = inst

        self.__crago = {} # type: typing.Dict[str, str]

        self.__num = 0

        # Need to check that is the path valid
        self.__path = path


        files = os.listdir(path)
        files = list(filter(lambda f: os.path.isfile(f), files))

        for f in files:
            self.__crago[f] = pathStrConcate(path, f, seperator = "/")

    def create(self, ident:str) -> typing.Optional[StoChooser]:
        if ident in self.__crago:
            return self.open(ident)

        path = pathStrConcate(self.__path, ident, seperator = "/")
        chooser = StoChooser(path)

        self.__crago[ident] = path

        return chooser

    def open(self, ident:str) -> typing.Optional[StoChooser]:

        if not ident in self.__crago:
            return self.create(ident)

        path = self.__crago[ident]
        chooser = StoChooser(path)

        return chooser
