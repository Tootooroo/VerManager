# postListener.py

import abc
import socket
import tempfile
import os
import platform
import time
import select
import traceback
import shutil

from datetime import datetime
from ..basic.util import spawnThread
from ..basic.letter import Letter, BinaryLetter, MenuLetter, \
    ResponseLetter, PostTaskLetter, LogLetter, LogRegLetter, \
    receving, sending
from ..basic.info import Info
from ..basic.mmanager import MManager, ModuleDaemon, Module, ModuleName
from ..basic.storage import Storage, StoChooser
from ..basic.type import *

from typing import Optional, Any, Tuple, List, Dict, Union
from threading import Thread, Lock
from queue import Queue, Empty as Q_Empty

from manager.basic.info import Info, M_NAME as INFO_M_NAME
from manager.worker.server import M_NAME as SERVER_M_NAME, Server

ReqIdent = Tuple[str, str]

M_NAME = "PostListener"

M_NAME_Provider = "PostProvider"

FilePath = str

# Log id
LOG_ID = "PostListener"

if platform.system() == 'Windows':
    sep = "&&"
    path_sep = "\\"
else:
    sep = ";"
    path_sep = "/"


class DISCONN(Exception): pass

class ProviderPorts(abc.ABC):

    @abc.abstractmethod
    def register(self, sock:socket.socket) -> None:
        """ Register a socket """

    @abc.abstractmethod
    def unregister(self, fd:int) -> None:
        """ Unregister a socket """

    @abc.abstractmethod
    def wait(self, timeout:int) -> List[Tuple[socket.socket, int]]:
        """
        Waiting for a ready provider

        timeout: timeout's unit is second
        """

    @abc.abstractmethod
    def isExists(sefl, fd) -> bool:
        """ Is a fd correspond to a provider is registered """

class WindowsPorts(ProviderPorts):

    def __init__(self) -> None:
        self.__providers = [] # type: List[socket.socket]

    def register(self, sock:socket.socket) -> None:
        if self.isExists(sock.fileno()):
            return None

        self.__providers.append(sock)

    def unregister(self, fd:int) -> None:
        if not self.isExists(fd):
            return None

        self.__providers = [
            provider
            for provider in self.__providers
            if provider.fileno() != fd
        ]

    def isExists(self, fd:int) -> bool:
        return fd in [sock.fileno() for sock in self.__providers]

    def wait(self, timeout:int) -> List[Tuple[socket.socket, int]]:

        if self.__providers == []:
            time.sleep(timeout)
            return []

        readies_r, readies_w, readies_x = \
            select.select(self.__providers, [], [], timeout)

        return list(zip(readies_r, [0] * len(readies_r)))


class LinuxPorts(ProviderPorts):

    def __init__(self) -> None:
        self.__socks = {} # type: Dict[int, socket.socket]
        self.__providers = select.poll()

    def register(self, sock:socket.socket) -> None:
        fd = sock.fileno()

        if fd in self.__socks:
            return None

        self.__socks[fd] = sock
        self.__providers.register(fd, select.POLLIN)

    def unregister(self, fd) -> None:
        if fd in self.__socks:
            del self.__socks [fd]
            self.__providers.unregister(fd)
        else:
            return None

    def wait(self, timeout:int) -> List[Tuple[socket.socket, int]]:
        timeout_seconds = timeout * 1000
        readies = self.__providers.poll(timeout)
        return [(self.__socks[fd], event) for (fd, event) in readies]

    def isExists(self, fd:int) -> bool:
        return fd in self.__socks


class PostListener(ModuleDaemon):

    def __init__(self, address:str, port:int, cInst:Any) -> None:
        global M_NAME
        ModuleDaemon.__init__(self, M_NAME)

        self.__address = address
        self.__port = port

        self.__cInst = cInst
        self.__processor = PostProcessor(cInst)

    def postAppend(self, postLetter:'PostTaskLetter') -> None:
        post = Post.fromPostLetter(postLetter) # type: Post
        self.__processor.appendPost(post)

    def postRemove(self, version:str) -> None:
        self.__processor.removePost(version)

    def run(self) -> None:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((self.__address, self.__port))
        s.listen(10)

        self.__processor.start()

        while True:
            (wSock, addr) = s.accept()

            wSock.settimeout(3)
            wSock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

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
        self.__stuffQ = Queue(1024)  # type: Queue[BinaryLetter]

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

    def provide(self, bin:BinaryLetter, timeout=None) -> State:
        self.__stuffQ.put(bin, timeout)
        return Ok

    def provide_step(self) -> State:

        inProcessing = True

        if self.__sock is None:
            return Error

        try:
            bin = self.__stuffQ.get_nowait()
        except Q_Empty:
            return Error

        while inProcessing:
            try:
                sending(self.__sock, bin)
            except Exception:
                # Interrupted, try to reconnect
                self.__sock = None

                while self.__sock is None:
                    print("Provide_ste: try to reconnect")
                    self.reconnect()

                    if self.__sock is not None:
                        break

                    time.sleep(3)

                continue

            inProcessing = False

        return Ok

class Post:

    # Describe a post-processing of a task
    # 1. Match frags and menus from providers and include
    #    match frags and menus.
    # 2. Contain informations that guid processor how
    #    to do post-processing.

    def __init__(self, ident:str, version:str, cmds:List[str], output:str,
                 menus:List['PostMenu'], frags:List[str]):

        self.__ident = ident
        self.__ver = version
        self.__cmds = cmds
        self.__output = output
        self.__menus = menus

        self.__frags = {} # type: Dict[str, PostFrag]
        for frag in frags:
            self.__frags[frag] = PostFrag(frag)

    def getIdent(self) -> str:
        return self.__ident

    def getVersion(self) -> str:
        return self.__ver

    def getMenus(self) -> List['PostMenu']:
        return self.__menus

    def getMenu(self, ident:str) -> Optional['PostMenu']:
        menus = list(filter(lambda menu: menu.getIdent(), self.__menus))

        if len(menus) > 0:
            return menus[0]

        return None

    def getCmds(self) -> List[str]:
        return self.__cmds

    def getOutput(self) -> str:
        return self.__output

    def getFrags(self) -> List[str]:
        return list(self.__frags.keys())

    def __menu_ids(self) -> List[str]:
        return list(map(lambda m: m.getIdent(), self.__menus))

    def isSatisfied(self) -> bool:

        for frag in self.__frags.values():
            if frag.stuff is None:
                return False

        for menu in self.__menus:
            if not menu.isSatisfied(): return False

        return True

    def match(self, stuff:'Stuff') -> bool:
        stuffName = stuff.name()

        if stuffName in self.__frags:
            self.__frags[stuffName].stuff = stuff
            return True

        for menu in self.__menus:
            isMatched = menu.stuffMatch(stuff)
            if isMatched:
                return True

        return False

    @staticmethod
    def fromPostLetter(letter:PostTaskLetter) -> 'Post':
        menus_ident = letter.menus()
        f = lambda mid: PostMenu.fromMenuLetter(letter.getMenu(mid))
        menus = list(map(f, menus_ident))

        return Post(letter.getIdent(),
                    letter.getVersion(),
                    letter.getCmds(),
                    letter.getOutput(),
                    menus,
                    letter.frags())


class PostFrag:

    def __init__(self, name:str, stuff:Optional['Stuff'] = None) -> None:
        self.name = name
        self.stuff = stuff

class PostMenu:

    def __init__(self, version:str, ident:str, depends:List[str],
                 cmd:List[str], output:str) -> None:

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
        return False not in list(self.__depends.values())

    def getCmd(self) -> List[str]:
        return self.__cmd

    @staticmethod
    def fromMenuLetter(letter:MenuLetter) -> 'PostMenu':
        return PostMenu(letter.getHeader('version'),
                        letter.getHeader('mid'),
                        letter.getContent('depends'),
                        letter.getContent('cmds'),
                        letter.getContent('output'))

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

    def __init__(self, version:str, menu:str, stuffName:str,
                 # Where's structure: (BoxName, FileName)
                 where:Tuple[str, str]) -> None:

        self.__version = version
        self.__menu = menu
        self.__stuffName = stuffName
        self.__where = where

        self.__last = datetime.utcnow()

    def elapsed(self) -> int:
        return (datetime.utcnow() - self.__last).seconds

    def version(self) -> str:
        return self.__version

    def menu(self) -> str:
        return self.__menu

    def name(self) -> str:
        return self.__stuffName

    def where(self) -> Tuple[str, str]:
        return self.__where

    def setMenu(self, menu:str) -> None:
        self.__menu = menu

    def setName(self, name:str) -> None:
        self.__stuffname = name

    def setWhere(self, where:Tuple[str, str]) -> None:
        self.__where =  where

class PostProcessor(Thread):

    def __init__(self, cInst:Any) -> None:
        Thread.__init__(self)

        self.__cInst = cInst

        # List of menu from server
        # after command of menu is
        # executed the menu will
        # be removed from this list
        self.__posts = [] # type: List[Post]
        self.__post_lock = Lock()

        self.__stuffs = Stuffs() # type: Stuffs

        self.__satisfiedPosts = Queue(10) # type: Queue[Post]

        system = platform.system()
        if system == 'Windows':
            self.__providers = WindowsPorts() # type: ProviderPorts
        elif system == 'Linux':
            self.__providers = LinuxPorts()

        self.__inProcReq = [] # type: List[ReqIdent]

        cfgs = cInst.getModule(INFO_M_NAME)
        self.__storage = Storage(cfgs.getConfig('PostStorage'), None)

        self.__chooserSet = {} # type: Dict[str, StoChooser]

        self.__server = None # type: Optional[Server]

    def logging(self, msg:str) -> None:
        global LOG_ID

        if self.__server is None:
            self.__server = self.__cInst.getModule(SERVER_M_NAME)

            if self.__server is not None:
                regLetter = LogRegLetter(self.__cInst.getIdent(), LOG_ID)
                self.__server.transfer(regLetter)
            else:
                return None

        log_letter = LogLetter(self.__cInst.getIdent(), LOG_ID, msg)
        self.__server.transfer(log_letter)

    def do_post_processing(self, post:Post) -> Optional[str]:

        buildDir = "Build"

        if not os.path.exists(buildDir):
            os.mkdir(buildDir)

        # Deal with menus
        menus = post.getMenus()
        states = list(map(lambda menu: self.__do_menu(menu, buildDir), menus))

        for menu in post.getMenus():
            if self.__do_menu(menu, buildDir) is Ok:
                self.logging("Menu " + menu.getIdent() + " is processed")
            else:
                self.logging("Menu " + menu.getIdent() + " failed")
                return None

        # fixme: need to copy frags to working directory
        cmds = post.getCmds()
        cmds.insert(0, "cd " + buildDir)
        cmds_str = sep.join(cmds)

        try:
            os.system(cmds_str)
        except:
            return None

        return buildDir

    def __do_menu(self, menu:PostMenu, workDir:FilePath) -> State:
        command = menu.getCmd()
        stuffs = menu.getStuffs()

        for stuff in stuffs:
            (boxName, fileName) = stuff.where()
            self.__storage.copyTo(boxName, fileName, workDir)

        command.insert(0, "cd " + workDir)
        command_str = sep.join(command)

        try:
            os.system(command_str)
        except:
            return Error

        output = menu.getOutput()

        # Cleanup
        for stuff in stuffs:
            (boxName, fileName) = stuff.where()
            self.__storage.delete(boxName, fileName)

        return Ok

    def run(self) -> None:

        spawnThread(self.__post_collect_stuffs)

        statisfied_posts = self.__satisfiedPosts

        configs = self.__cInst.getModule(INFO_M_NAME)
        workerIdent = self.__cInst.getIdent()

        server = self.__cInst.getModule(SERVER_M_NAME)

        while True:

            post = statisfied_posts.get()
            self.logging("Post " + post.getVersion() + " is in processing")

            postId = post.getIdent()
            version = post.getVersion()
            response = ResponseLetter(workerIdent, postId, Letter.RESPONSE_STATE_FINISHED)

            wDir = self.do_post_processing(post)
            if wDir is None:
                self.logging("Post " + post.getVersion() + " is failed")

                # Notify master this post is failed.
                response.setState(Letter.RESPONSE_STATE_FAILURE)
                server.transfer(response)
                continue

            output = post.getOutput()
            fileName = output.split(path_sep)[-1]

            if output[0] == ".":
                output = "Build" + path_sep + output

            try:
                with open(output, "rb") as binFile:
                    for bytes in binFile:

                        try:
                            binaryLetter = BinaryLetter(
                                postId, bytes,
                                parent = version,
                                fileName = fileName)

                            server.transfer(binaryLetter)

                        except BinaryLetter.FIELD_LENGTH_EXCEPTION:
                            response.setState(Letter.RESPONSE_STATE_FAILURE)
                            server.transfer(response)

                            # Remove working directory
                            shutil.rmtree(wDir)
                            return None

                    lastBin  = BinaryLetter(
                        postId, b"",
                        parent = version,
                        fileName = fileName)
                    server.transfer(lastBin)

            except FileNotFoundError:
                response.setState(Letter.RESPONSE_STATE_FAILURE)

            server.transfer(response)

            # Remove working directory
            shutil.rmtree(wDir)


    def appendPost(self, post:Post) -> None:
        with self.__post_lock:
            self.__posts.append(post)

    def removePost(self, version:str) -> None:
        with self.__post_lock:

            for post in self.__posts:
                if post.getIdent() == version:
                    self.__posts.remove(post)

    # Retrive information and binary file from workers and store into __pends
    def __post_collect_stuffs(self, args = None) -> None:

        while True:
            providers = self.__providers.wait(1)

            # Build stuffs from binary from providers
            for sock, event in providers:
                self.__build_stuff(sock)

            # Pair stuffs with menus
            stuff = self.__stuffs.popHead()

            if stuff is None:
                continue

            self.logging("Stuff arrived: " + stuff.name())

            isPaired = self.__post_stuff_pair(stuff)

            # fixme: add a counter to this stuff so we can remove
            #        a stuff if it's counter's value is bigger than
            #        a specific value.
            if isPaired is False:
                # Only retry to pair stuff within last 5 seconds.
                if stuff.elapsed() < 5:
                    self.__stuffs.addStuff(stuff)
            else:
                self.logging("Stuff " + stuff.name() + " paired")

            # After match we need to check is there a menu which
            # collect all stuffs of it need

            with self.__post_lock:
                for post in self.__posts:
                    if post.isSatisfied():
                        self.__satisfiedPosts.put(post)
                        self.__posts.remove(post)



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
            except socket.timeout:
                break
            except Exception:
                traceback.print_exc()

            # if parse error
            if letter is None or not isinstance(letter, BinaryLetter):
                return None

            content = letter.getContent('bytes')
            tid = letter.getTid()
            version = letter.getParent()
            stoId = PostProcessor.__stoIdGen(tid, version)
            menu = letter.getMenu()
            fileName = letter.getFileName()

            # The last binary letter
            if content == b"":
                if stoId not in self.__chooserSet:
                    return None

                self.__chooserSet[stoId].close()
                del self.__chooserSet [stoId]


                stuff = Stuff(version, menu, tid, (version, fileName))
                self.__stuffs.addStuff(stuff)

                return None


            if stoId not in self.__chooserSet:

                # Create a file in storage
                fileName = letter.getFileName()
                chooser = storage.create(version, fileName)

                if chooser is None:
                    return None

                self.__chooserSet[stoId] = chooser

            chooser = self.__chooserSet[stoId]

            if isinstance(content, bytes) and chooser is not None:
                chooser.store(content)

    def __post_stuff_pair(self, stuff:Stuff) -> bool:
        posts = self.__posts


        with self.__post_lock:
            for post in posts:
                if post.match(stuff):
                    return True

        return False

    @staticmethod
    def __stoIdGen(tid:str, parent:str) -> str:
        return parent+"__"+tid

    @staticmethod
    def __receving(sock: socket.socket) -> Optional[Letter]:
        try:
            return receving(sock)
        except BlockingIOError:
            raise BlockingIOError
        except socket.timeout:
            raise socket.timeout
        except Exception:
            raise DISCONN

    def __addSock(self, sock:socket.socket) -> State:

        fd = sock.fileno()

        if self.__providers.isExists(fd):
            return Error

        self.__providers.register(sock)

        return Ok

    def __rmSock(self, descriptor:Union[socket.socket, int]) -> State:

        fd = 0

        if isinstance(descriptor, socket.socket):
            fd = descriptor.fileno()
        else:
            fd = descriptor

        if not self.__providers.isExists(fd):
            return Error

        self.__providers.unregister(fd)

        return Ok


    def req(self, sock:socket.socket) -> None:
        self.__addSock(sock)
