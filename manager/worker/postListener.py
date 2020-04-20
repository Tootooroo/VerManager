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
from ..basic.util import spawnThread, sockKeepalive
from ..basic.letter import Letter, BinaryLetter, MenuLetter, \
    ResponseLetter, PostTaskLetter, LogLetter, LogRegLetter, \
    receving, sending
from ..basic.info import Info
from ..basic.mmanager import MManager, ModuleDaemon, Module, ModuleName
from ..basic.storage import Storage, StoChooser
from ..basic.type import *
from ..basic.request import LastLisAddrRequire

from typing import Optional, Any, Tuple, List, Dict, Union
from threading import Thread, Lock
from queue import Queue, Empty as Q_Empty

from manager.basic.info import Info, M_NAME as INFO_M_NAME
from manager.worker.server import M_NAME as SERVER_M_NAME, Server
from manager.basic.observer import Observer

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
        self._providers = [] # type: List[socket.socket]

    def register(self, sock:socket.socket) -> None:
        if self.isExists(sock.fileno()):
            return None

        self._providers.append(sock)

    def unregister(self, fd:int) -> None:
        if not self.isExists(fd):
            return None

        self._providers = [
            provider
            for provider in self._providers
            if provider.fileno() != fd
        ]

    def isExists(self, fd:int) -> bool:
        return fd in [sock.fileno() for sock in self._providers]

    def wait(self, timeout:int) -> List[Tuple[socket.socket, int]]:

        if self._providers == []:
            time.sleep(timeout)
            return []

        readies_r, readies_w, readies_x = \
            select.select(self._providers, [], [], timeout)

        return list(zip(readies_r, [0] * len(readies_r)))


class LinuxPorts(ProviderPorts):

    def __init__(self) -> None:
        self._socks = {} # type: Dict[int, socket.socket]
        self._providers = select.poll()

    def register(self, sock:socket.socket) -> None:
        fd = sock.fileno()

        if fd in self._socks:
            return None

        self._socks[fd] = sock
        self._providers.register(fd, select.POLLIN)

    def unregister(self, fd) -> None:
        if fd in self._socks:
            del self._socks [fd]
            self._providers.unregister(fd)
        else:
            return None

    def wait(self, timeout:int) -> List[Tuple[socket.socket, int]]:
        timeout_seconds = timeout * 1000
        readies = self._providers.poll(timeout)
        return [(self._socks[fd], event) for (fd, event) in readies]

    def isExists(self, fd:int) -> bool:
        return fd in self._socks


class PostListener(ModuleDaemon, Observer):

    def __init__(self, address:str, port:int, cInst:Any) -> None:
        global M_NAME
        ModuleDaemon.__init__(self, M_NAME)
        Observer.__init__(self)

        self._sock = None # type: Optional[socket.socket]
        self._isStop = False
        self._address = address
        self._port = port
        self._master_lock = Lock()

        self._cInst = cInst
        self._processor = PostProcessor(cInst)

    def begin(self) -> None:
        return None

    def postAppend(self, postLetter:'PostTaskLetter') -> None:
        post = Post.fromPostLetter(postLetter) # type: Post
        self._processor.appendPost(post)

    def postRemove(self, version:str) -> None:
        self._processor.removePost(version)

    def postRemoveAll(self) -> None:
        self._processor.removeAllPost()

    def masterSock(self) -> State:
        with self._master_lock:

            if self._sock is not None:
                return Ok

            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.bind((self._address, self._port))
                s.listen(10)
                s.settimeout(5)

                self._sock = s
                print("PostListener listen at " + str((self._address, self._port)) )
            except:
                import traceback; traceback.print_exc()
                self._sock = None
                return Error

        return Ok


    def address_update(self, data:Tuple[int, str]) -> None:
        """
        Handler to processing message from processor that about
        the listener's address is changed.
        """
        role, address = data

        # PostListener should not to concern
        # such a message.
        if role != 0:
            return None

        if self._address != address:
            self._address = address

            if self._sock is not None:
                self._sock.close()

            self._sock = None

    def run(self) -> None:

        self.masterSock()
        self._processor.start()

        while True:
            if self._isStop:
                self._processor.stop()
                if self._sock is not None:
                    self._sock.close()

                break

            if self._sock is None:
                if self.masterSock() == Error:
                    time.sleep(3)
                    continue

            try:
                (wSock, addr) = self._sock.accept() # type: ignore
            except socket.timeout:
                continue
            except AttributeError:
                # self._sock may be None during
                # PostListener's addres updating
                continue
            except OSError:
                continue

            wSock.settimeout(3)
            sockKeepalive(wSock, 10, 3)

            self._processor.req(wSock)

    def cleanup(self) -> None:
        return None

    def stop(self) -> None:
        self._isStop = True

class PostProvider(Module, Observer):

    UPPER_LIMIT_TO_REQUIRE_ADDR = 10
    ADDR_REQUIRE_INTERVAL = 5

    def __init__(self, address:str, port:int, cInst:Any, connect:bool = False) -> None:
        global M_NAME_Provider

        Module.__init__(self, M_NAME_Provider)
        Observer.__init__(self)

        self._address = address
        self._port = port
        self._sock = None # type: Optional[socket.socket]
        self._stuffQ = Queue(1024)  # type: Queue[BinaryLetter]
        self._Q_lock = Lock()
        self._cInst = cInst

        self._isStop = False

        # If _num_of_failed reach the limit worker should
        # acquire last address of listener from master.
        self._upper_limit = PostProvider.UPPER_LIMIT_TO_REQUIRE_ADDR
        # Num of failed to reconnect to PostListener
        self._num_of_failed = 0
        # Clock to control address request rate
        self._last_time_to_acquire_addr = datetime.utcnow()

        if connect: self.connectToListener()

    def setAddress(self, address:str, port:int) -> None:
        self._address = address
        self._port = port

    def address_update(self, data: Tuple[int, str]) -> None:

        role, address = data

        # PostProvider should not to concern such
        # a message.
        if role != 1:
            return None

        if self._address != address:
            self.setAddress(address, 8066)

        self._sock = None
        self.connectToListener(1)



    def connectToListener(self, retry:int = 0) -> State:
        retry += 1

        sock = self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        while True:

            # Update counter
            retry -= 1

            try:
                #print("Try to connect to " + self._address + ":" + str(self._port))
                sock.connect((self._address, self._port))
                break

            except:
                if retry > 0:
                    time.sleep(1)
                    continue
                else:
                    sock.close()
                    self._sock = None
                    return Error

            break

        return Ok

    def reconnect(self, retry:int = 0) -> State:
        if self._sock is not None:
            self._sock.close()
            self._sock = None

        ret = self.connectToListener(retry)

        if ret == Error:
            self._num_of_failed += 1

            # In that case worker should acquire last address
            # of PostListener from master.
            if self._num_of_failed >= self._upper_limit:
                # Allow only one request to address in a 5 seconds.
                now = datetime.utcnow()
                interval = (now - self._last_time_to_acquire_addr).seconds
                if interval < PostProvider.ADDR_REQUIRE_INTERVAL:
                    return Error
                else:
                    self._last_time_to_acquire_addr = now

                server = self._cInst.getModule(SERVER_M_NAME) # type: Optional[Server]
                if server is None:
                    return Error

                workerName = self._cInst.getIdent()
                req = LastLisAddrRequire(workerName)
                server.transfer(req.toLetter())

                self._num_of_failed = 0

            return Error

        return Ok

    def sock(self) -> Optional[socket.socket]:
        return self._sock

    def disconnect(self) -> None:
        if self._sock is not None:
            self._sock.shutdown(socket.SHUT_RDWR)
            self._sock.close()
            self._sock = None

    def provide(self, bin:BinaryLetter, timeout=None) -> State:
        self._stuffQ.put(bin, timeout=timeout)
        return Ok

    def provide_step(self) -> State:

        if self._isStop:
            return Error

        inProcessing = True

        if self._sock is None:
            if self.reconnect() == Error:
                return Error

        with self._Q_lock:
            try:
                bin = self._stuffQ.get_nowait()
            except Q_Empty:
                return Error

            while inProcessing:
                try:
                    if self._sock is None:
                        raise Exception

                    sending(self._sock, bin)
                except Exception:
                    print("Provide_ste: try to reconnect")
                    if self.reconnect() == Error:
                        # Put into head of queue
                        self._stuffQ.queue.insert(0, bin) # type: ignore
                    else:
                        continue

                inProcessing = False

        return Ok

    def removeAllStuffs(self) -> None:
        with self._Q_lock:
            self._stuffQ.queue.clear() # type: ignore

    def begin(self) -> None:
        return None

    def cleanup(self) -> None:
        self.disconnect()
        self._sock = None

        self._isStop = True

class Post:

    # Describe a post-processing of a task
    # 1. Match frags and menus from providers and include
    #    match frags and menus.
    # 2. Contain informations that guid processor how
    #    to do post-processing.

    def __init__(self, ident:str, version:str, cmds:List[str], output:str,
                 menus:List['PostMenu'], frags:List[str]) -> None:

        self._ident = ident
        self._ver = version
        self._cmds = cmds
        self._output = output
        self._menus = menus

        self._frags = {} # type: Dict[str, PostFrag]
        for frag in frags:
            self._frags[frag] = PostFrag(frag)

    def getIdent(self) -> str:
        return self._ident

    def getVersion(self) -> str:
        return self._ver

    def getMenus(self) -> List['PostMenu']:
        return self._menus

    def getMenu(self, ident:str) -> Optional['PostMenu']:
        menus = list(filter(lambda menu: menu.getIdent(), self._menus))

        if len(menus) > 0:
            return menus[0]

        return None

    def getCmds(self) -> List[str]:
        return self._cmds

    def getOutput(self) -> str:
        return self._output

    def getFrags(self) -> List[str]:
        return list(self._frags.keys())

    def _menu_ids(self) -> List[str]:
        return list(map(lambda m: m.getIdent(), self._menus))

    def isSatisfied(self) -> bool:

        for frag in self._frags.values():
            if frag.stuff is None:
                return False

        for menu in self._menus:
            if not menu.isSatisfied(): return False

        return True

    def match(self, stuff:'Stuff') -> bool:
        stuffName = stuff.name()

        if stuffName in self._frags:
            self._frags[stuffName].stuff = stuff
            return True

        for menu in self._menus:
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

        self._version = version
        self._ident = ident
        self._cmd = cmd
        self._depends = {} # type: Dict[str, bool]
        self._output = output

        # Things that need by cmd
        self._stuffs = Stuffs() # type: Stuffs
        self._stuffs.setVersion(version)

        for d in depends:
            self._depends[d] = False

    def getVersion(self) -> str:
        return self._version

    def getIdent(self) -> str:
        return self._ident

    def stuffMatch(self, stuff:'Stuff') -> bool:
        stuffName = stuff.name()

        if stuffName not in self._depends:
            return False

        version = stuff.version()

        # Version not paired
        if self._version != version:
            return False

        # This stuff must not exists in this menu
        assert(not self._stuffs.isExists(stuffName))

        self._stuffs.addStuff(stuff)
        self._depends[stuffName] = True

        return True

    def getOutput(self) -> str:
        return self._output

    def getStuffs(self) -> List['Stuff']:
        return self._stuffs.toList()

    def isSatisfied(self) -> bool:
        return False not in list(self._depends.values())

    def getCmd(self) -> List[str]:
        return self._cmd

    @staticmethod
    def fromMenuLetter(letter:MenuLetter) -> 'PostMenu':
        return PostMenu(letter.getHeader('version'),
                        letter.getHeader('mid'),
                        letter.getContent('depends'),
                        letter.getContent('cmds'),
                        letter.getContent('output'))

class Stuffs:

    def __init__(self) -> None:
        self._version = None # type: Optional[str]
        self._stuffs = {} # type: Dict[str, Stuff]

        self._lock = Lock()

        self._stuffs_list = [] # type: List[Stuff]
        self._index = 0
        self._len = 0

    def _iter_(self) -> 'Stuffs':
        return self

    def _next_(self) -> 'Stuff':

        with self._lock:
            index = self._index
            self._index += 1

        return self._stuffs_list[index]

    def popHead(self) -> Optional['Stuff']:

        self._lock.acquire()

        if self._len > 0:
            elem = self._stuffs_list[0]
        else:
            self._lock.release()
            return None

        self._stuffs_list.remove(elem)

        ident = elem.name()
        del self._stuffs [ident]

        self._len -= 1

        self._lock.release()

        return elem

    def toList(self) -> List['Stuff']:
        return list(self._stuffs.values())

    def setVersion(self, version:str) -> None:
        self._version = version

    def getVersion(self) -> Optional[str]:
        return self._version

    def getStuff(self, stuffName:str) -> Optional['Stuff']:
        with self._lock:
            if not stuffName in self._stuffs:
                return None
            return self._stuffs[stuffName]

    def isExists(self, stuffName:str) -> bool:
        return stuffName in self._stuffs

    def addStuff(self, stuff:'Stuff') -> None:
        stuffName = stuff.name()

        with self._lock:
            # if version has been set then only stuff which
            # version is same with self._version can be
            # added
            if not self._version is None:
                if stuff.version() != self._version:
                    return None

            if stuffName in self._stuffs:
                return None

            self._stuffs[stuffName] = stuff
            self._stuffs_list.append(stuff)
            self._len += 1

    def removeStuff(self, name:str) -> None:
        with self._lock:
            if not name in self._stuffs:
                return None

            del self._stuffs [name]
            self._len -= 1

class Stuff:

    def __init__(self, version:str, menu:str, stuffName:str,
                 # Where's structure: (BoxName, FileName)
                 where:Tuple[str, str]) -> None:

        self._version = version
        self._menu = menu
        self._stuffName = stuffName
        self._where = where

        self._last = datetime.utcnow()

    def elapsed(self) -> int:
        return (datetime.utcnow() - self._last).seconds

    def version(self) -> str:
        return self._version

    def menu(self) -> str:
        return self._menu

    def name(self) -> str:
        return self._stuffName

    def where(self) -> Tuple[str, str]:
        return self._where

    def setMenu(self, menu:str) -> None:
        self._menu = menu

    def setName(self, name:str) -> None:
        self._stuffname = name

    def setWhere(self, where:Tuple[str, str]) -> None:
        self._where =  where

class PostProcessor(Thread):

    def __init__(self, cInst:Any) -> None:
        Thread.__init__(self)

        self._cInst = cInst

        # List of menu from server
        # after command of menu is
        # executed the menu will
        # be removed from this list
        self._posts = [] # type: List[Post]
        self._post_lock = Lock()

        self._stuffs = Stuffs() # type: Stuffs

        self._satisfiedPosts = Queue(10) # type: Queue[Post]

        system = platform.system()
        if system == 'Windows':
            self._providers = WindowsPorts() # type: ProviderPorts
        elif system == 'Linux':
            self._providers = LinuxPorts()

        self._inProcReq = [] # type: List[ReqIdent]

        cfgs = cInst.getModule(INFO_M_NAME)
        self._storage = Storage(cfgs.getConfig('PostStorage'), None)

        self._chooserSet = {} # type: Dict[str, StoChooser]

        self._server = None # type: Optional[Server]

        self._isStop = False

    def stop(self) -> None:
        self._isStop = True

    def logging(self, msg:str) -> None:
        global LOG_ID

        if self._server is None:
            self._server = self._cInst.getModule(SERVER_M_NAME)

            if self._server is not None:
                regLetter = LogRegLetter(self._cInst.getIdent(), LOG_ID)
                self._server.transfer(regLetter)
            else:
                return None

        log_letter = LogLetter(self._cInst.getIdent(), LOG_ID, msg)
        self._server.transfer(log_letter)

    def do_post_processing(self, post:Post) -> Optional[str]:

        buildDir = "Build"

        if not os.path.exists(buildDir):
            os.mkdir(buildDir)

        # Deal with menus
        menus = post.getMenus()
        states = list(map(lambda menu: self._do_menu(menu, buildDir), menus))

        for menu in post.getMenus():
            if self._do_menu(menu, buildDir) is Ok:
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

    def _do_menu(self, menu:PostMenu, workDir:FilePath) -> State:
        command = menu.getCmd()
        stuffs = menu.getStuffs()

        for stuff in stuffs:
            (boxName, fileName) = stuff.where()
            self._storage.copyTo(boxName, fileName, workDir)

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
            self._storage.delete(boxName, fileName)

        return Ok

    def run(self) -> None:

        spawnThread(self._post_collect_stuffs)

        statisfied_posts = self._satisfiedPosts

        configs = self._cInst.getModule(INFO_M_NAME)
        workerIdent = self._cInst.getIdent()

        server = self._cInst.getModule(SERVER_M_NAME)

        while True:

            if self._isStop:
                break

            try:
                post = statisfied_posts.get(timeout=5)
            except Q_Empty:
                continue

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
        with self._post_lock:
            self._posts.append(post)

    def removePost(self, version:str) -> None:
        with self._post_lock:

            for post in self._posts:
                if post.getIdent() == version:
                    self._posts.remove(post)

    def removeAllPost(self) -> None:
        with self._post_lock:
            self._posts = []

    # Retrive information and binary file from workers and store into _pends
    def _post_collect_stuffs(self, args = None) -> None:

        while True:

            if self._isStop:
                break

            providers = self._providers.wait(1)

            # Build stuffs from binary from providers
            for sock, event in providers:
                self._build_stuff(sock)

            # Pair stuffs with menus
            stuff = self._stuffs.popHead()

            if stuff is None:
                continue

            self.logging("Stuff arrived: " + stuff.name())

            isPaired = self._post_stuff_pair(stuff)

            # fixme: add a counter to this stuff so we can remove
            #        a stuff if it's counter's value is bigger than
            #        a specific value.
            if isPaired is False:
                # Only retry to pair stuff within last 5 seconds.
                if stuff.elapsed() < 15:
                    self._stuffs.addStuff(stuff)
            else:
                self.logging("Stuff " + stuff.name() + " paired")

            # After match we need to check is there a menu which
            # collect all stuffs of it need

            with self._post_lock:
                for post in self._posts:
                    if post.isSatisfied():
                        self._satisfiedPosts.put(post)
                        self._posts.remove(post)



    # Return (tid, parent, stoId)
    def _build_stuff(self, sock:socket.socket) -> None:

        storage = self._storage
        chooser = None # type: Optional[StoChooser]

        tid = ""

        letter = None # type: Optional[Letter]

        while True:
            try:
                letter = self._receving(sock)
            except DISCONN:
                self._rmSock(sock)
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
            stoId = PostProcessor._stoIdGen(tid, version)
            menu = letter.getMenu()
            fileName = letter.getFileName()

            # The last binary letter
            if content == b"":
                if stoId not in self._chooserSet:
                    return None

                self._chooserSet[stoId].close()
                del self._chooserSet [stoId]


                stuff = Stuff(version, menu, tid, (version, fileName))
                self._stuffs.addStuff(stuff)

                return None


            if stoId not in self._chooserSet:

                # Create a file in storage
                fileName = letter.getFileName()
                chooser = storage.create(version, fileName)

                if chooser is None:
                    return None

                self._chooserSet[stoId] = chooser

            chooser = self._chooserSet[stoId]

            if isinstance(content, bytes) and chooser is not None:
                chooser.store(content)

    def _post_stuff_pair(self, stuff:Stuff) -> bool:
        posts = self._posts


        with self._post_lock:
            for post in posts:
                if post.match(stuff):
                    return True

        return False

    @staticmethod
    def _stoIdGen(tid:str, parent:str) -> str:
        return parent+"_"+tid

    @staticmethod
    def _receving(sock: socket.socket) -> Optional[Letter]:
        try:
            return receving(sock)
        except BlockingIOError:
            raise BlockingIOError
        except socket.timeout:
            raise socket.timeout
        except Exception:
            raise DISCONN

    def _addSock(self, sock:socket.socket) -> State:

        fd = sock.fileno()

        if self._providers.isExists(fd):
            return Error

        self._providers.register(sock)

        return Ok

    def _rmSock(self, descriptor:Union[socket.socket, int]) -> State:

        fd = 0

        if isinstance(descriptor, socket.socket):
            fd = descriptor.fileno()
        else:
            fd = descriptor

        if not self._providers.isExists(fd):
            return Error

        self._providers.unregister(fd)

        return Ok


    def req(self, sock:socket.socket) -> None:
        self._addSock(sock)
