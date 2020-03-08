# Storage

import os
import platform
import shutil
import traceback

from typing import Optional, Dict, BinaryIO, Any, List, IO

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

    def fd(self) -> BinaryIO:
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

class File:

    def __init__(self, name:str, path:str) -> None:
        self.name = name
        self.__path = path

    def open(self) -> BinaryIO:
        return open(self.__path, "rb")

    def remove(self) -> None:
        os.remove(self.__path)

    def path(self) -> str:
        return self.__path

class Box:

    def __init__(self, ident:str, where:'Storage') -> None:
        self.__ident = ident

        self.__where = where
        self.__files = {} # type: Dict[str, File]

        self.__path = where.sotragePath() + seperator + ident

        if not os.path.exists(self.__path):
            os.makedirs(self.__path)
        else:
            self.__recover()

    def __recover(self) -> None:
        files = os.listdir(self.__path)

        files = list(filter(lambda f: os.path.isfile(f), files))
        if len(files) == 0:
            return None



    def files(self) -> List[File]:
        return list(self.__files.values())

    def getFile(self, fileName:str) -> File:
        return self.__files[fileName]

    def exists(self, fileName:str) -> bool:
        return fileName in self.__files

    def add(self, fileName:str, file:File) -> None:

        if self.exists(fileName):
            return None

        self.__files[fileName] = file

    def remove(self, fileName:str) -> None:

        if not self.exists(fileName):
            return None

        theFile = self.__files[fileName]

        try:
            theFile.remove()
        except:
            pass

        del self.__files [fileName]

    def path(self) -> str:
        return self.__where.sotragePath() + seperator + self.__ident

    def newFile(self, name) -> Optional[StoChooser]:
        if name in self.__files:
            return None

        filePath = self.path() + seperator + name
        file = File(name, filePath)

        self.add(name, file)

        return StoChooser(filePath)

class Storage(Module):

    def __init__(self, path:str, inst:Any) -> None:

        Module.__init__(self, "")

        self.__sInst = inst
        self.__crago = {} # type: Dict[str, Box]
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
    def __addDirToCrago(crago:Dict[str, Box], path:str) -> None:
        global seperator

        files = os.listdir(path)
        files = list(filter(lambda f: os.path.isfile(f), files))
        files = list(map(lambda f: Storage.__trimExtension(f), files))

        for f in files:
            crago[f] = pathStrConcate(path, f, seperator = seperator)

    def recover(self) -> None:
        pass

    def create(self, ident:str, fileName:str, box:Optional[str]=None) -> Optional[StoChooser]:
        global seperator

        if ident in self.__crago:
            return self.open(ident)

        if box is None:
            path = pathStrConcate(self.__path, fileName, seperator = seperator)
        else:
            path = pathStrConcate(self.__path, box, fileName, seperator=seperator)

        dirs = seperator.join(path.split(seperator)[0:-1])
        fileName = path.split(seperator)[-1]

        if not os.path.exists(dirs):
            os.makedirs(dirs)

        chooser = StoChooser(path)

        self.__crago[ident] = path
        self.__num += 1

        return chooser

    def open(self, ident:str, box:Optional[str]=None) -> Optional[StoChooser]:

        if not ident in self.__crago:
            return None

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

    def getPath(self, ident:str) -> Optional[str]:
        if not ident in self.__crago:
            return ""

        return self.__crago[ident]

    def sotragePath(self) -> str:
        return self.__path

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
