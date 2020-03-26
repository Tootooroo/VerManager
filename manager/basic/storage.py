# Storage

import os
import platform
import shutil
import traceback

from functools import reduce
from typing import Optional, Dict, BinaryIO, Any, List, IO

from .mmanager import Module
from manager.basic.type import *
from manager.basic.util import pathStrConcate

if platform.system() == 'Windows':
    seperator = "\\"
else:
    seperator = "/"

M_NAME = "Storage"

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

        # File is an object to describe a file on disk.
        # If a file on disk is not exists. The object
        # should not be able to create.
        if not os.path.exists(path):
            with open(self.__path, "wb") as f : pass

    def open(self) -> StoChooser:
        return StoChooser(self.__path)

    def remove(self) -> None:
        os.remove(self.__path)

    def path(self) -> str:
        return self.__path

class Box:

    def __init__(self, name:str, where:'Storage') -> None:
        self.__ident = name

        self.__where = where
        self.__files = {} # type: Dict[str, File]

        self.__path = where.sotragePath() + seperator + name

        if not os.path.exists(self.__path):
            os.makedirs(self.__path)
        else:
            self.__recover()

    def __recover(self) -> State:
        files = os.listdir(self.__path)

        files = list(filter(lambda f: os.path.isfile(f), files))
        if len(files) == 0:
            return Ok

        for fileName in files:
            filePath = self.__path + seperator + fileName
            file = File(fileName, filePath)

            self.__files[fileName] = file

        return Ok

    def files(self) -> List[File]:
        return list(self.__files.values())

    def getFile(self, fileName:str) -> Optional[File]:
        if fileName not in self.__files: return None
        return self.__files[fileName]

    def openFile(self, fileName:str) -> Optional[StoChooser]:
        if fileName not in self.__files: return None
        return self.__files[fileName].open()

    def exists(self, fileName:str) -> bool:
        return fileName in self.__files

    def add(self, fileName:str, file:File) -> None:
        if self.exists(fileName): return None

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

    def newFile(self, name:str) -> Optional[StoChooser]:
        if name in self.__files:
            return None

        filePath = self.path() + seperator + name
        file = File(name, filePath)

        self.add(name, file)

        return StoChooser(filePath)

    def copyFrom(self, filePath:str, fileName:str) -> State:
        # Copy a file specified by the filePath to this box.

        if self.exists(fileName):
            return Error

        newFilePath = self.__path + seperator + fileName
        shutil.copy(filePath, newFilePath)
        f = File(fileName, newFilePath)

        return Ok

    def copyTo(self, fileName:str, filePath:str) -> State:
        # Copy a file from given location to this box

        if not self.exists(fileName):
            return Error

        f = self.getFile(fileName)
        if f is None: return Error

        shutil.copy(f.path(), filePath)

        return Ok

    def numOfFiles(self) -> int:
        return len(self.__files)

class Storage(Module):

    def __init__(self, path:str, inst:Any) -> None:

        Module.__init__(self, M_NAME)

        self.__sInst = inst
        self.__boxes = {} # type: Dict[str, Box]
        self.__num = 0

        # Need to check that is the path valid
        self.__path = path

        # Add target directory's file into Storage
        if os.path.exists(path):
            self.__recover()
        else:
            os.makedirs(path)

    def __recover(self) -> None:
        global seperator

        boxes = os.listdir(self.__path)
        boxes = list(filter(lambda f: os.path.isdir(f), boxes))

        for boxName in boxes:
            box = Box(boxName, self)
            self.__boxes[boxName] = box

    def recover(self) -> None:
        self.__recover

    def create(self, boxName:str, fileName:str) -> Optional[StoChooser]:
        """
        Create a file within a box if the box is not exists then Create
        that box and then create the file with given fileName.

        If the file already exists then return chooser of that file.
        """
        global seperator

        if boxName == "" or fileName == "":
            return None

        if boxName not in self.__boxes:
            self.__createBox(boxName)

        theBox = self.__getBox(boxName)
        assert(theBox is not None)

        f = theBox.getFile(fileName)
        if f is not None: return f.open()

        # The file is not exist.
        return theBox.newFile(fileName)

    def __createBox(self, boxName:str) -> State:
        if self.__isExists(boxName):
            return Error

        self.__boxes[boxName] = Box(boxName, self)
        return Ok

    def __getBox(self, boxName:str) -> Optional[Box]:
        if boxName not in self.__boxes:
            return None
        return self.__boxes[boxName]

    def open(self, boxName:str, fileName:str) -> Optional[StoChooser]:
        if boxName not in self.__boxes:
            return None

        theBox = self.__boxes[boxName]
        return theBox.openFile(fileName)

    def delete(self, boxName:str, fileName:str) -> None:
        """
        Delete a file specified by the fileName of the box specified by boxName.
        """
        if boxName not in self.__boxes:
            return None

        box = self.__boxes[boxName]
        box.remove(fileName)

        if box.numOfFiles() == 0:
            del self.__boxes [boxName]
            os.rmdir(box.path())

    def __isExists(self, boxName:str) -> bool:
        return boxName in self.__boxes

    def isFileExists(self, boxName:str, fileName:str) -> bool:
        pass

    def numOfFiles(self) -> int:
        total = 0

        for box in self.__boxes.values():
            total += box.numOfFiles()

        return total

    def getFile(self, boxName:str, fileName:str) -> Optional[File]:
        if boxName not in self.__boxes:
            return None

        theBox = self.__getBox(boxName)
        if theBox is None:
            return None

        return theBox.getFile(fileName)

    def filesOf(self, boxName:str) -> List[File]:
        if boxName not in self.__boxes:
            return []

        box = self.__boxes[boxName]
        return box.files()

    def sotragePath(self) -> str:
        return self.__path

    def copyFrom(self, filePath:str, boxName:str, fileName:str) -> State:

        if not os.path.isfile(filePath):
            # File support only.
            return Error

        theBox = self.__getBox(boxName)
        if theBox is None:
            return Error

        return theBox.copyFrom(filePath, fileName)

    def copyTo(self, boxName:str, fileName:str, dest:str) -> State:

        if not boxName in self.__boxes:
            return Error

        theBox = self.__getBox(boxName)
        if theBox is None:
            return Error

        return theBox.copyTo(fileName, dest)
