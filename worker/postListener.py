# client_post.py

from client import Client
from server import Server
from post import Post
from receiver import Receiver
from sender import Sender
from processor import Processor

from basic.util import spawnThread
from basic.letter import Letter
from basic.info import Info
from basic.mmanager import MManager, ModuleDaemon, Module, ModuleName
from basic.storage import Storage, StoChooser

from typing import Optional, Any, Tuple, List, Dict
from threading import Thread, Lock
from queue import Queue

import socket

ReqIdent = Tuple[str, str]

class PostListener(ModuleDaemon):

    def __init__(self, address:str, port:int, cInst:Any) -> None:
        ModuleDaemon.__init__(self, "")

        self.__address = address
        self.__port = port

        self.__cInst = cInst
        self.__processor = PostProcessor()

    def reqAppend(self, parent:str, tid:str, stoId:str) -> None:
        self.__processor.appendPend(parent, tid, stoId)


    def run(self) -> None:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((self.__address, self.__port))
        s.listen(10)

        self.__processor.start()

        while True:
            (wSock, addr) = s.accept()

            self.__processor.req(wSock)

class PostMenu:

    def __init__(self, depends:List[str], cmd:str) -> None:
        self.__cmd = cmd
        self.__depends = {} # type: Dict[str, bool]

        # Things that need by cmd
        self.__stuffs = Stuffs() # type: Stuffs

        for d in depends:
            self.__depends[d] = False

    def pairDepend(self, stuff:Stuff) -> bool:
        stuffName = stuff.name()

        if not stuffName in self.__depends:
            return False

        versionOfStuffs = self.__stuffs.getVersion()
        version = stuff.version()

        # Setup version to stuffs
        if versionOfStuffs is None:
            self.__stuffs.setVersion(version)

        # Version not paired
        if versionOfStuffs != version:
            return False

        # Already exists
        if self.__stuffs.isExists(stuffName):
            return False

        self.__stuffs.addStuff(stuff)
        self.__depends[stuffName] = True

        return True


    def isSatisfied(self) -> bool:
        return not False in list(self.__depends.values())

    def getCmd(self) -> str:
        return self.__cmd

class Stuffs:

    def __init__(self) -> None:
        self.__version = None # type: Optional[str]
        self.__stuffs = {} # type: Dict[str, Stuff]

        self.__stuffs_list = [] # type: List[Stuff]
        self.__index = 0
        self.__len = 0

    def __iter__(self) -> Stuffs:
        return self

    def __next__(self) -> Stuff:
        index = self.__index
        self.__index += 1

        return self.__stuffs_list[index]

    def toList(self) -> List[Stuff]:
        return list(self.__stuffs.values())

    def setVersion(self, version:str) -> None:
        self.__version = version

    def getVersion(self) -> Optional[str]:
        return self.__version

    def getStuff(self, stuffName:str) -> Optional['Stuff']:
        if not stuffName in self.__stuffs:
            return None
        return self.__stuffs[stuffName]

    def isExists(self, stuffName:str) -> bool:
        return stuffName in self.__stuffs

    def addStuff(self, stuff:Stuff) -> None:
        stuffName = stuff.name()

        # if version has been set then only stuff which
        # version is same with self.__version can be
        # added
        if not self.__version is None:
            if stuff.version() != self.__version:
                return None

        if stuffName in self.__stuffs:
            return None

        self.__stuffs[stuffName] = stuff
        self.__stuffs_list.append(stuff)
        self.__len += 1

class Stuff:

    def __init__(self, version:str, menu:str, stuffName:str, where:str) -> None:
        self.__version = version
        self.__menu = menu
        self.__stuffName = stuffName
        self.__where = where

    def version(self) -> str:
        return self.__version

    def menu(self) -> str:
        return self.__menu

    def name(self) -> str:
        return self.__stuffName

    def where(self) -> str:
        return self.__where

    def setMenu(self, menu:str) -> None:
        self.__menu = menu

    def setName(self, name:str) -> None:
        self.__stuffname = name

    def setWhere(self, where:str) -> None:
        self.__where =  where

class PostProcessor(Thread):

    def __init__(self) -> None:
        Thread.__init__(self)

        # List of menu from server
        # after command of menu is
        # executed the menu will
        # be removed from this list
        self.__menus = [] # type: List[PostMenu]

        self.__stuffs = Stuffs() # type: Stuffs
        self.__stuffs_lock = Lock()

        self.__reqQueue = Queue(10) # type: Queue[socket.socket]
        self.__inProcReq = [] # type: List[ReqIdent]
        self.__storage = Storage("./PostStorage", None)
        self.__chooserSet = {} # type: Dict[str, StoChooser]

    def run(self) -> None:

        spawnThread(self.__pend_proc)

        lock = self.__stuffs_lock

        while True:

            with self.__stuffs_lock:
                stuffs = self.__stuffs.toList()

            for stuff in stuffs:
                pass




    def appendMenu(self, menu:PostMenu) -> None:
        self.__menus.append(menu)

    def appendStuff(self, stuff:Stuff) -> None:
        with self.__stuffs_lock:
            self.__stuffs.addStuff(stuff)

    # Retrive information and binary file from workers and store into __pends
    def __pend_proc(self, args) -> None:

        while True:
            sock = self.__reqQueue.get()

            ret = self.__binary_recv(sock)

            if ret is None:
                return None

            version = ret[0]
            tid = ret[1]
            stoId = ret[2]
            menu = ret[3]

            stuff = Stuff(version, menu, tid, stoId)

            self.appendStuff(stuff)

    # Return (tid, parent, stoId)
    def __binary_recv(self, sock:socket.socket) -> Optional[Tuple[str, str, str, str]]:

        checkFlag = False
        storage = self.__storage
        chooser = None # type: Optional[StoChooser]

        tid = ""

        while True:
            try:
                letter = self.__receving(sock)
            except:
                break

            # if parse error
            if letter is None:
                return None

            tid = letter.getHeader("tid")
            parent = letter.getHeader("parent")
            menu = letter.getHeader("menu")
            stoId = PostProcessor.__stoIdGen(parent, tid)

            if checkFlag is False:
                checkFlag = True

                # There should no several same tasks be processed
                # by VersionManager at a time.
                if storage.isExists(stoId):
                    storage.delete(stoId)

                # Create a file in storage
                extension = letter.getHeader("extension")
                chooser = storage.create(stoId, extension)

                if chooser is None:
                    return None

                self.__chooserSet[stoId] = chooser

            content = letter.getContent('bytes')

            if isinstance(content, str):
                return None

            chooser.store(content) # type: ignore

        if tid == "":
            return None

        return (tid, parent, stoId, menu)


    @staticmethod
    def __stoIdGen(tid:str, parent:str) -> str:
        return parent+"__"+tid



    @staticmethod
    def __receving(sock: socket.socket) -> Optional[Letter]:
        content = b''
        remain = Letter.BINARY_HEADER_LEN

        while remain > 0:
            chunk = sock.recv(remain)
            if chunk == b'':
                raise Exception

            content += chunk
            remain = Letter.letterBytesRemain(content)

        return Letter.parse(content)

    def req(self, sock:socket.socket) -> None:
        self.__reqQueue.put(sock)
