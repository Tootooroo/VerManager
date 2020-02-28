# Storage

import typing
import os
import platform
import shutil
import traceback

from .mmanager import Module
from manager.basic.type import *
from manager.basic.util import pathStrConcate

if platform.system() == 'Windows':
    seperator = "\\"
else:
    seperator = "/"

class STORAGE_IDENT_NOT_FOUND(Exception):
    pass

class StoChooser:

    def __init__(self, path:str) -> None:

        self.__path = path

        try:
            self.__fd = open(path, "a+b")
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

    def rewind(self) -> None:
        fd = self.__fd
        fd.seek(0, 0)


class Storage(Module):

    def __init__(self, path:str, inst:typing.Any) -> None:

        Module.__init__(self, "")

        self.__sInst = inst
        self.__crago = {} # type: typing.Dict[str, str]
        self.__num = 0

        # Need to check that is the path valid
        self.__path = path

        # Add target directory's file into Storage
        Storage.__addDirToCrago(self.__crago, path)

    @staticmethod
    def __trimExtension(name:str) -> str:
        parts = name.split(".")

        if len(parts) == 1:
            return name
        elif len(parts) > 1:
            return ''.join(parts[0:-1])
        else:
            return ""

    @staticmethod
    def __addDirToCrago(crago:typing.Dict[str, str], path:str) -> None:
        global seperator

        files = os.listdir(path)
        files = list(filter(lambda f: os.path.isfile(f), files))
        files = list(map(lambda f: Storage.__trimExtension(f), files))

        for f in files:
            crago[f] = pathStrConcate(path, f, seperator = seperator)

    def create(self, ident:str, ext:str = '') -> typing.Optional[StoChooser]:
        global seperator

        if ident in self.__crago:
            return self.open(ident)

        path = pathStrConcate(self.__path, ident, seperator = seperator)
        if ext != '':
            path += "." + ext

        chooser = StoChooser(path)

        self.__crago[ident] = path
        self.__num += 1

        return chooser

    def open(self, ident:str) -> typing.Optional[StoChooser]:

        if not ident in self.__crago:
            return self.create(ident)

        path = self.__crago[ident]
        chooser = StoChooser(path)

        return chooser

    def delete(self, ident:str) -> None:

        if not ident in self.__crago:
            return None

        path = self.__crago[ident]

        try:
            os.remove(path)
        except FileNotFoundError:
            pass

        del self.__crago [ident]
        self.__num -= 1

    def isExists(self, ident:str) -> bool:
        return ident in self.__crago

    def numOfFiles(self) -> int:
        return self.__num

    def getPath(self, ident:str) -> typing.Optional[str]:
        if not ident in self.__crago:
            return ""

        return self.__crago[ident]

    # User should make sure filePath is within Storage's path
    def __addNewFile(self, ident, filePath:str) -> State:
        if ident in self.__crago:
            return Error

        self.__crago[ident] = filePath
        return Ok

    def copy(self, filePath:str) -> State:

        if len(filePath) < 1:
            return Error

        if os.path.isfile(filePath):
            copyMethod = shutil.copy
        elif os.path.isdir(filePath):
            copyMethod = shutil.copytree # type: ignore

        targetFile = filePath.split(seperator)[-1]
        stoIdent = targetFile.split(".")[-1]

        dest = self.__path + seperator + targetFile

        try:
            copyMethod(filePath, dest)
        except:
            return Error

        self.__addNewFile(stoIdent, dest)

        return Ok

    def copyTo(self, ident:str, dest:str) -> State:

        if dest == "":
            return Error

        if not ident in self.__crago:
            return Error

        path = self.__crago[ident]

        try:
            shutil.copy(path, dest)
        except:
            traceback.print_exc()
            return Error

        return Ok
