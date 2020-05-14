# Storage

import os
import platform
import shutil

from typing import Optional, Dict, BinaryIO, Any, List

from .mmanager import Module
from manager.basic.type import State, Ok, Error

if platform.system() == 'Windows':
    seperator = "\\"
else:
    seperator = "/"

M_NAME = "Storage"


class STORAGE_IDENT_NOT_FOUND(Exception):
    pass


class StoChooser:

    def __init__(self, path:  str) -> None:

        self._path = path

        try:
            self._fd = open(path, "wb")
        except FileNotFoundError:
            raise STORAGE_IDENT_NOT_FOUND

    def fd(self) -> BinaryIO:
        return self._fd

    def setFd(self, fd) -> State:
        self._fd = fd

        return Ok

    def path(self) -> str:
        return self._path

    def isValid(self) -> bool:
        return True

    def store(self, content: bytes) -> None:

        fd = self._fd

        fd.write(content)

    def retrive(self, count: int) -> bytes:

        fd = self._fd

        content = fd.read(count)

        return content

    def close(self) -> State:
        fd = self._fd
        fd.close()

        return Ok

    def rewind(self) -> None:
        fd = self._fd
        fd.seek(0, 0)


class File:

    def __init__(self, name: str, path: str) -> None:
        self.name = name
        self._path = path

        # File is an object to describe a file on disk.
        # If a file on disk is not exists. The object
        # should not be able to create.
        if not os.path.exists(path):
            open(self._path, "wb")

    def open(self) -> StoChooser:
        return StoChooser(self._path)

    def remove(self) -> None:
        os.remove(self._path)

    def path(self) -> str:
        return self._path


class Box:

    def __init__(self, name: str, where: 'Storage') -> None:
        self._ident = name

        self._where = where
        self._files = {}  # type:  Dict[str, File]

        self._path = where.sotragePath() + seperator + name

        if not os.path.exists(self._path):
            os.makedirs(self._path)
        else:
            self._recover()

    def _recover(self) -> State:
        files = os.listdir(self._path)

        files = list(filter(lambda f:  os.path.isfile(self._path+seperator+f),
                            files))
        if len(files) == 0:
            return Ok

        for fileName in files:
            filePath = self._path + seperator + fileName
            file = File(fileName, filePath)

            self._files[fileName] = file

        return Ok

    def files(self) -> List[File]:
        return list(self._files.values())

    def getFile(self, fileName: str) -> Optional[File]:
        if fileName not in self._files:
            return None
        return self._files[fileName]

    def openFile(self, fileName: str) -> Optional[StoChooser]:
        if fileName not in self._files:
            return None
        return self._files[fileName].open()

    def exists(self, fileName: str) -> bool:
        return fileName in self._files

    def add(self, fileName: str, file: File) -> None:
        if self.exists(fileName):
            return None

        self._files[fileName] = file

    def remove(self, fileName: str) -> None:

        if not self.exists(fileName):
            return None

        theFile = self._files[fileName]

        try:
            theFile.remove()
        except Exception:
            pass

        del self._files[fileName]

    def path(self) -> str:
        return self._where.sotragePath() + seperator + self._ident

    def newFile(self, name: str) -> Optional[StoChooser]:
        if name in self._files:
            return None

        filePath = self.path() + seperator + name
        file = File(name, filePath)

        self.add(name, file)

        return StoChooser(filePath)

    def copyFrom(self, filePath: str, fileName: str) -> State:
        # Copy a file specified by the filePath to this box.

        if self.exists(fileName):
            return Error

        newFilePath = self._path + seperator + fileName
        shutil.copy(filePath, newFilePath)
        File(fileName, newFilePath)

        return Ok

    def copyTo(self, fileName: str, filePath: str) -> State:
        # Copy a file from given location to this box

        if not self.exists(fileName):
            return Error

        f = self.getFile(fileName)
        if f is None:
            return Error

        shutil.copy(f.path(), filePath)

        return Ok

    def numOfFiles(self) -> int:
        return len(self._files)


class Storage(Module):

    def __init__(self, path: str, inst: Any) -> None:

        Module.__init__(self, M_NAME)

        self._sInst = inst
        self._boxes = {}  # type:  Dict[str, Box]
        self._num = 0

        # Need to check that is the path valid
        self._path = path

        # Add target directory's file into Storage
        if os.path.exists(path):
            self._recover()
        else:
            os.makedirs(path)

    def begin(self) -> None:
        return None

    def cleanup(self) -> None:
        return None

    def _recover(self) -> None:
        global seperator

        boxes = os.listdir(self._path)
        boxes = list(filter(lambda f:  os.path.isdir(self._path+seperator+f),
                            boxes))

        for boxName in boxes:
            box = Box(boxName, self)
            self._boxes[boxName] = box

    def recover(self) -> None:
        self._recover()

    def create(self, boxName: str, fileName: str) -> Optional[StoChooser]:
        """
        Create a file within a box if the box is not exists then Create
        that box and then create the file with given fileName.

        If the file already exists then return chooser of that file.
        """
        global seperator

        if boxName == "" or fileName == "":
            return None

        if boxName not in self._boxes:
            self._createBox(boxName)

        theBox = self._getBox(boxName)
        assert(theBox is not None)

        f = theBox.getFile(fileName)
        if f is not None:
            return f.open()

        # The file is not exist.
        return theBox.newFile(fileName)

    def _createBox(self, boxName: str) -> State:
        if self._isExists(boxName):
            return Error

        self._boxes[boxName] = Box(boxName, self)
        return Ok

    def _getBox(self, boxName: str) -> Optional[Box]:
        if boxName not in self._boxes:
            return None
        return self._boxes[boxName]

    def open(self, boxName: str, fileName: str) -> Optional[StoChooser]:
        if boxName not in self._boxes:
            return None

        theBox = self._boxes[boxName]
        return theBox.openFile(fileName)

    def delete(self, boxName: str, fileName: str) -> None:
        """
        Delete a file specified by the fileName
        of the box specified by boxName.
        """
        if boxName not in self._boxes:
            return None

        box = self._boxes[boxName]
        box.remove(fileName)

        if box.numOfFiles() == 0:
            del self._boxes[boxName]
            os.rmdir(box.path())

    def _isExists(self, boxName: str) -> bool:
        return boxName in self._boxes

    def isFileExists(self, boxName: str, fileName: str) -> bool:
        pass

    def numOfFiles(self) -> int:
        total = 0

        for box in self._boxes.values():
            total += box.numOfFiles()

        return total

    def getFile(self, boxName: str, fileName: str) -> Optional[File]:
        if boxName not in self._boxes:
            return None

        theBox = self._getBox(boxName)
        if theBox is None:
            return None

        return theBox.getFile(fileName)

    def filesOf(self, boxName: str) -> List[File]:
        if boxName not in self._boxes:
            return []

        box = self._boxes[boxName]
        return box.files()

    def sotragePath(self) -> str:
        return self._path

    def copyFrom(self, filePath: str, boxName: str, fileName: str) -> State:

        if not os.path.isfile(filePath):
            # File support only.
            return Error

        theBox = self._getBox(boxName)
        if theBox is None:
            return Error

        return theBox.copyFrom(filePath, fileName)

    def copyTo(self, boxName: str, fileName: str, dest: str) -> State:

        if boxName not in self._boxes:
            return Error

        theBox = self._getBox(boxName)
        if theBox is None:
            return Error

        return theBox.copyTo(fileName, dest)

    def destruct(self) -> None:
        shutil.rmtree(self._path)
