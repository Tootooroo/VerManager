# client_post.py

import socket
import tempfile
import os
import platform

from client import Client
from server import Server
from post import Post
from receiver import Receiver
from sender import Sender
from processor import Processor

from basic.util import spawnThread
from basic.letter import Letter, BinaryLetter
from basic.info import Info
from basic.mmanager import MManager, ModuleDaemon, Module, ModuleName
from basic.storage import Storage, StoChooser

from typing import Optional, Any, Tuple, List, Dict
from threading import Thread, Lock
from queue import Queue

ReqIdent = Tuple[str, str]

class PostListener(ModuleDaemon):

    def __init__(self, address:str, port:int, cInst:Any) -> None:
        ModuleDaemon.__init__(self, "")

        self.__address = address
        self.__port = port

        self.__cInst = cInst
        self.__processor = PostProcessor(cInst)

    def reqAppend(self, stuff:'Stuff') -> None:
        self.__processor.appendStuff(stuff)

    def menuAppend(self, menu:'PostMenu') -> None:
        self.__processor.appendMenu(menu)

    def run(self) -> None:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((self.__address, self.__port))
        s.listen(10)

        self.__processor.start()

        while True:
            (wSock, addr) = s.accept()

            self.__processor.req(wSock)

class PostMenu:

    def __init__(self, depends:List[str], cmd:str, output:str) -> None:
        self.__cmd = cmd
        self.__depends = {} # type: Dict[str, bool]
        self.__output = output

        # Things that need by cmd
        self.__stuffs = Stuffs() # type: Stuffs

        for d in depends:
            self.__depends[d] = False

    def stuffMatch(self, stuff:Stuff) -> bool:
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

    def getOutput(self) -> str:
        return self.__output

    def getStuffs(self) -> List[Stuff]:
        return self.__stuffs.toList()

    def isSatisfied(self) -> bool:
        return not False in list(self.__depends.values())

    def getCmd(self) -> str:
        return self.__cmd

class Stuffs:

    def __init__(self) -> None:
        self.__version = None # type: Optional[str]
        self.__stuffs = {} # type: Dict[str, Stuff]

        self.__lock = Lock()

        self.__stuffs_list = [] # type: List[Stuff]
        self.__index = 0
        self.__len = 0

    def __iter__(self) -> 'Stuffs':
        return self

    def __next__(self) -> 'Stuff':

        with self.__lock:
            index = self.__index
            self.__index += 1

        return self.__stuffs_list[index]

    def popHead(self) -> Optional['Stuff']:

        self.__lock.acquire()

        if self.__len > 0:
            elem = self.__stuffs_list[0]
        else:
            return None

        self.__stuffs_list.remove(elem)

        ident = elem.name()
        del self.__stuffs [ident]

        self.__lock.release()

        return elem

    def toList(self) -> List[Stuff]:
        return list(self.__stuffs.values())

    def setVersion(self, version:str) -> None:
        self.__version = version

    def getVersion(self) -> Optional[str]:
        return self.__version

    def getStuff(self, stuffName:str) -> Optional['Stuff']:
        with self.__lock:
            if not stuffName in self.__stuffs:
                return None
            return self.__stuffs[stuffName]

    def isExists(self, stuffName:str) -> bool:
        return stuffName in self.__stuffs

    def addStuff(self, stuff:Stuff) -> None:
        stuffName = stuff.name()

        with self.__lock:
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

    def removeStuff(self, name:str) -> None:
        with self.__lock:
            if not name in self.__stuffs:
                return None

            del self.__stuffs [name]

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

    def __init__(self, cInst:Any) -> None:
        Thread.__init__(self)

        self.__cInst = cInst

        # List of menu from server
        # after command of menu is
        # executed the menu will
        # be removed from this list
        self.__menus = [] # type: List[PostMenu]
        self.__menus_lock = Lock()

        self.__stuffs = Stuffs() # type: Stuffs

        self.__satisfiedMenus = Queue(10) # type: Queue[PostMenu]

        self.__reqQueue = Queue(10) # type: Queue[socket.socket]
        self.__inProcReq = [] # type: List[ReqIdent]
        self.__storage = Storage("./PostStorage", None)
        self.__chooserSet = {} # type: Dict[str, StoChooser]

    def run(self) -> None:

        spawnThread(self.__menu_collect_stuffs)

        menu_queue = self.__satisfiedMenus

        if platform.system() == 'Windows':
            sep = "&&"
        else:
            sep = ";"

        while True:

            menu = menu_queue.get()

            command = menu.getCmd()
            stuffs = menu.getStuffs()

            workingDir = tempfile.TemporaryDirectory()

            for stuff in stuffs:
                self.__storage.copyTo(stuff.where(), workingDir.name)

            command = "cd " + workingDir.name + sep + command

            os.system(command)

            # Output of command should be a file
            output = menu.getOutput()
            if not os.path.isfile(output):
                continue

            # Cleanup
            for stuff in stuffs:
                self.__storage.delete(stuff.name())

            server = self.__cInst.getModule('Server')

            with open("output", "rb") as output_file:

                for line in output_file:
                    binaryLetter = BinaryLetter(stuff.name(), line,
                                                menu = stuff.menu(),
                                                extension = "rar",
                                                parent = stuff.version())
                    server.transfer(binaryLetter)


    def appendMenu(self, menu:PostMenu) -> None:
        with self.__menus_lock:
            self.__menus.append(menu)

    def appendStuff(self, stuff:Stuff) -> None:
        self.__stuffs.addStuff(stuff)

    # Retrive information and binary file from workers and store into __pends
    def __menu_collect_stuffs(self, args) -> None:

        while True:
            try:
                sock = self.__reqQueue.get(timeout = 1) # type: Optional[socket.socket]
            except:
                sock = None

            if sock is None:
                stuff = self.__stuffs.popHead()
            else:
                stuff = self.__build_stuff(sock)

            if stuff is None:
                continue

            isPaired = self.__menu_stuff_pair(stuff)

            # fixme: add a counter to this stuff so we can remove
            #        a stuff if it's counter's value is bigger than
            #        a specific value.
            if isPaired is False:
                self.__stuffs.addStuff(stuff)

            # After match we need to check is there a menu which
            # collect all stuffs of it need
            self.__menus_lock.acquire()

            for menu in self.__menus:
                isSatisfied = menu.isSatisfied()

                if isSatisfied:
                    self.__satisfiedMenus.put(menu)

            self.__menus_lock.release()



    # Return (tid, parent, stoId)
    def __build_stuff(self, sock:socket.socket) -> Optional[Stuff]:

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
            version = letter.getHeader("parent")
            menu = letter.getHeader("menu")
            stoId = PostProcessor.__stoIdGen(version, tid)

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

        return Stuff(version, menu, tid, stoId)

    def __menu_stuff_pair(self, stuff:Stuff) -> bool:
        menus = self.__menus

        self.__menus_lock.acquire()

        for menu in menus:
            isMatched = menu.stuffMatch(stuff)

            if isMatched:
                break

        self.__menus_lock.release()

        return isMatched


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
