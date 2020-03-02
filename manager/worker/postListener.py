# postListener.py

import socket
import tempfile
import os
import platform
import time
import select
import traceback

from ..basic.util import spawnThread
from ..basic.letter import Letter, BinaryLetter, MenuLetter, ResponseLetter
from ..basic.info import Info
from ..basic.mmanager import MManager, ModuleDaemon, Module, ModuleName
from ..basic.storage import Storage, StoChooser
from ..basic.type import *

from typing import Optional, Any, Tuple, List, Dict, Union
from threading import Thread, Lock
from queue import Queue

from manager.worker.server import M_NAME as SERVER_M_NAME

ReqIdent = Tuple[str, str]

M_NAME = "PostListener"

M_NAME_Provider = "PostProvider"

class DISCONN(Exception):
    pass

class PostListener(ModuleDaemon):

    def __init__(self, address:str, port:int, cInst:Any) -> None:
        global M_NAME
        ModuleDaemon.__init__(self, M_NAME)

        self.__address = address
        self.__port = port

        self.__cInst = cInst
        self.__processor = PostProcessor(cInst)

    def reqAppend(self, stuff:'Stuff') -> None:
        self.__processor.appendStuff(stuff)

    def menuAppend(self, menuLetter:'MenuLetter') -> None:
        menu = PostMenu(menuLetter.getHeader('version'),
                        menuLetter.getHeader('mid'),
                        menuLetter.getContent('depends'),
                        menuLetter.getContent('cmds'),
                        menuLetter.getContent('output'))
        self.__processor.appendMenu(menu)

    def run(self) -> None:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((self.__address, self.__port))
        s.listen(10)

        self.__processor.start()

        while True:
            (wSock, addr) = s.accept()

            wSock.setblocking(False)
            wSock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            wSock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 10)
            wSock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 1)
            wSock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)

            self.__processor.req(wSock)

    def stop(self) -> None:
        pass

class PostProvider(Module):

    def __init__(self, address:str, port:int, connect:bool = False) -> None:
        global M_NAME_Provider

        Module.__init__(self, M_NAME_Provider)
        self.__address = address
        self.__port = port
        self.__sock = None # type: Optional[socket.socket]

        if connect:
            self.connectToListener()

    def connectToListener(self, retry:int = 1) -> State:

        if not self.__sock is None:
            return Error

        sock = self.__sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        while retry > 0:

            try:
                sock.connect((self.__address, self.__port))
            except:

                self.__sock = None

                time.sleep(1)
                retry -= 1

            break

        return Ok

    def reconnect(self, retry:int = 1) -> State:
        if self.__sock is None:
            return Error

        return self.connectToListener(retry)

    def disconnect(self) -> None:
        if not self.__sock is None:
            self.__sock.close()
            self.__sock = None

    def provide(self, bin:BinaryLetter) -> State:

        if self.__sock is None:
            return Error

        byteStr = bin.toBytesWithLength()

        totalSent = 0
        length = len(byteStr)

        if byteStr is None:
            return Error

        while totalSent < length:
            try:
                sent = self.__sock.send(byteStr[totalSent:])

                if sent == 0:
                    return Error

                totalSent += sent
            except BrokenPipeError:
                # Set __sock to None so we are
                # able to reconnect to listener
                # with a new socket
                self.__sock = None
                self.reconnect()

                # Failed to reconnect
                if self.__sock is None:
                    return Error

                continue

        return Ok


class PostMenu:

    def __init__(self, version:str, ident:str, depends:List[str], cmd:List[str], output:str) -> None:
        self.__version = version
        self.__ident = ident
        self.__cmd = cmd
        self.__depends = {} # type: Dict[str, bool]
        self.__output = output

        # Things that need by cmd
        self.__stuffs = Stuffs() # type: Stuffs
        self.__stuffs.setVersion(version)

        for d in depends:
            self.__depends[d] = False

    def getVersion(self) -> str:
        return self.__version

    def getIdent(self) -> str:
        return self.__ident

    def stuffMatch(self, stuff:'Stuff') -> bool:
        stuffName = stuff.name()

        if stuffName not in self.__depends:
            return False

        version = stuff.version()

        # Version not paired
        if self.__version != version:
            return False

        # This stuff must not exists in this menu
        assert(not self.__stuffs.isExists(stuffName))

        self.__stuffs.addStuff(stuff)
        self.__depends[stuffName] = True

        return True

    def getOutput(self) -> str:
        return self.__output

    def getStuffs(self) -> List['Stuff']:
        return self.__stuffs.toList()

    def isSatisfied(self) -> bool:
        return not False in list(self.__depends.values())

    def getCmd(self) -> List[str]:
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
            self.__lock.release()
            return None

        self.__stuffs_list.remove(elem)

        ident = elem.name()
        del self.__stuffs [ident]

        self.__len -= 1

        self.__lock.release()

        return elem

    def toList(self) -> List['Stuff']:
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

    def addStuff(self, stuff:'Stuff') -> None:
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
            self.__len -= 1

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

        self.__socks = {} # type: Dict[int, socket.socket]

        # List of menu from server
        # after command of menu is
        # executed the menu will
        # be removed from this list
        self.__menus = [] # type: List[PostMenu]
        self.__menus_lock = Lock()

        self.__stuffs = Stuffs() # type: Stuffs

        self.__satisfiedMenus = Queue(10) # type: Queue[PostMenu]

        self.__providers = select.poll()
        self.__inProcReq = [] # type: List[ReqIdent]
        self.__storage = Storage("./PostStorage", None)
        self.__chooserSet = {} # type: Dict[str, StoChooser]

    def run(self) -> None:

        spawnThread(self.__menu_collect_stuffs)

        statisfied_menus = self.__satisfiedMenus

        if platform.system() == 'Windows':
            sep = "&&"
            path_sep = "\\"
        else:
            sep = ";"
            path_sep = "/"

        while True:

            menu = statisfied_menus.get()

            command = menu.getCmd()
            stuffs = menu.getStuffs()

            workingDir = tempfile.TemporaryDirectory()

            for stuff in stuffs:
                self.__storage.copyTo(stuff.where(), workingDir.name)

            command.insert(0, "cd " + workingDir.name)

            command_str = sep.join(command)

            # Need a way to stop commands
            # with os.system() we are unable to
            # stop commands
            os.system(command_str)

            # Output of command should be a file
            output = menu.getOutput()
            if not os.path.isfile(output):
                continue

            # Cleanup
            for stuff in stuffs:
                self.__storage.delete(stuff.name())

            server = self.__cInst.getModule(SERVER_M_NAME)

            with open(output, "rb") as output_file:

                for line in output_file:
                    binaryLetter = BinaryLetter(stuff.name(), line,
                                                menu = stuff.menu(),
                                                fileName = output.split(path_sep)[-1],
                                                parent = stuff.version())
                    server.transfer(binaryLetter)

            # Transfer fin letter after binary
            finLetter = ResponseLetter(menu.getIdent(), Letter.RESPONSE_STATE_FINISHED,
                                       menu.getVersion())

            server.transfer(finLetter)


    def appendMenu(self, menu:PostMenu) -> None:
        with self.__menus_lock:
            self.__menus.append(menu)

    def appendStuff(self, stuff:Stuff) -> None:
        self.__stuffs.addStuff(stuff)

    # Retrive information and binary file from workers and store into __pends
    def __menu_collect_stuffs(self, args = None) -> None:

        while True:
            providers = self.__providers.poll(1000)

            # Build stuffs from binary from providers
            for fd, event in providers:
                sock = self.__socks[fd]
                self.__build_stuff(sock)

            # Pair stuffs with menus
            stuff = self.__stuffs.popHead()

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
    def __build_stuff(self, sock:socket.socket) -> None:

        storage = self.__storage
        chooser = None # type: Optional[StoChooser]

        tid = ""

        letter = None # type: Optional[Letter]

        while True:
            try:
                letter = self.__receving(sock)
            except DISCONN:
                self.__rmSock(sock)
                break
            except BlockingIOError as e:
                if e.errno == 11:
                    break

            # if parse error
            if letter is None:
                return None

            content = letter.getContent('bytes')
            tid = letter.getHeader('tid')
            version = letter.getHeader("parent")
            stoId = PostProcessor.__stoIdGen(tid, version)

            # the last binary letter
            if content == b"":
                self.__chooserSet[stoId].close()
                del self.__chooserSet [stoId]

                tid = letter.getHeader("tid")
                menu = letter.getHeader("menu")

                self.__stuffs.addStuff(Stuff(version, menu, tid, stoId))

                continue


            if stoId not in self.__chooserSet:

                # Create a file in storage
                extension = letter.getHeader("extension")
                chooser = storage.create(stoId, extension)

                if chooser is None:
                    return None

                self.__chooserSet[stoId] = chooser

            chooser = self.__chooserSet[stoId]

            if isinstance(content, bytes) and chooser is not None:
                chooser.store(content)

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
                raise DISCONN

            content += chunk
            remain = Letter.letterBytesRemain(content)

        return Letter.parse(content)

    def __addSock(self, sock:socket.socket) -> State:

        fd = sock.fileno()

        if fd in self.__socks:
            return Error

        self.__socks[fd] = sock
        self.__providers.register(fd, select.POLLIN)

        return Ok

    def __rmSock(self, descriptor:Union[socket.socket, int]) -> State:

        fd = 0

        if isinstance(descriptor, socket.socket):
            fd = descriptor.fileno()
        else:
            fd = descriptor

        if not fd in self.__socks:
            return Error

        del self.__socks [fd]
        self.__providers.unregister(fd)

        return Ok


    def req(self, sock:socket.socket) -> None:
        self.__addSock(sock)
