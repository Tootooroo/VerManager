# server.py
# Usage: python server.py <configPath>

import sys
import os
import socket
import time
import platform
import typing

from threading import Lock
import traceback

if __name__ == '__main__':
    from basic.letter import *
    from basic.info import Info
    from basic.type import *
    from basic.util import partition
else:
    from .basic.letter import *
    from .basic.info import Info
    from .basic.type import *
    from .basic.util import partition

from multiprocessing import Pool, Queue, Manager
from multiprocessing.pool import AsyncResult
from threading import Thread, Condition

class DISCONN_EXCEPTION(Exception):
    pass

class StopableThread(Thread):

    def stop(self) -> None:
        pass

class Module:
    pass

class ModuleT(Module, StopableThread):
    pass

def extensionFromPath(path:str) -> str:
    fileName = path.split("/")[-1]
    nameParts = fileName.split(".")

    if '' in nameParts:
        return ""

    if len(nameParts) == 1:
        return ""
    else:
        return nameParts[-1]

class Sender(ModuleT):

    def __init__(self, server, info, cInst:Client) -> None:
        Thread.__init__(self)

        self.cond = Condition()
        self.server = server

        self.__status = 0

    def stop(self) -> None:
        self.__status = 1

    def run(self) -> None:
        cond = self.cond
        server = self.server

        cond.acquire()

        while True:

            if self.__status == 1:
                self.__status = 2
                cond.release()
                return None

            try:
                ret = server.transfer_step(1)
            except:
                continue

            while ret == Error:
                # Waiting for <Receiver> reconnecting
                time.sleep(5)
                continue

class Recyler(ModuleT):

    def __init__(self, cInst:Client) -> None:
        Thread.__init__(self)

        receiver = cInst.getModule('Receiver')
        if not isinstance(receiver, Receiver):
            raise Exception

        self.tasks = receiver.inProcTasks
        self.t = receiver

        self.__status = 0

    def status(self) -> int:
        return self.__status

    def stop(self) -> None:
        self.__status = 1

    def run(self) -> None:
        while True:
            if self.__status == 1:
                self.__status = 2
                return None

            for key in list(self.tasks.keys()):
                task = self.tasks[key]

                if task.ready() == True:
                    self.t.numOfTasksInProc -= 1
                    del self.tasks [key]

            time.sleep(0.05)



class Processor(Module):

    def __init__(self, info, cInst:Client) -> None:
        self.__max = int(info.getConfig('MAX_TASK_CAN_PROC'))
        self.__numOfTasksInProc = 0
        self.__cInst = cInst
        self.__poolSize = int(info.getConfig('PROCESS_POLL_SIZE'))
        self.__pool = Pool(self.__poolSize)
        self.__info = info

        self.__allTasks = [] # type: List[Tuple[str, AsyncResult]]
        # Query purpose
        self.__allTasks_dict = {} # type: Dict[str, AsyncResult]

    def maxTasksAbleToProc(self) -> int:
        return self.__max

    def tasksInProc(self) -> int:
        return self.__numOfTasksInProc

    def poolSize(self) -> int:
        return self.__poolSize

    def proc(self, reqLetter:NewLetter) -> State:

        if not self.isAbleToProc():
            return Error

        tid = reqLetter.getHeader('tid')
        if self.isReqInProc(tid):
            return Error

        s = self.__cInst.getModule("Server")

        res = self.__pool.apply_async(Processor.__do_proc, (s, reqLetter, self.__info))
        self.__numOfTasksInProc += 1

        self.__allTasks.append((tid, res))
        self.__allTasks_dict[tid] = res

        return Ok

    @staticmethod
    def __do_proc(server:Server, post:Post, reqLetter:NewLetter, info:Info) -> None:

        WORKER_NAME = info.getConfig('WORKER_NAME')

        extra = reqLetter.getContent("extra")
        building_cmds = extra['cmds']
        result_path = extra['resultPath']

        if platform.system() == "Windows":
            result_path = result_path.replace("/", "\\")
            building_cmds = result_path.replace(";", "&&")

        # Notify master this task is change into in_processing state
        response = ResponseLetter(ident = WORKER_NAME,
                                  tid = vsn, state = Letter.RESPONSE_STATE_IN_PROC) # type: ignore
        server.transfer(response)

        # Processing
        try:
            repo_url = info.getConfig("REPO_URL")
            projName = info.getConfig("PROJECT_NAME")

            ret = os.system("git clone -b master " + repo_url)

            os.chdir(projName)

            revision = reqLetter.getContent('sn')
            ret = os.system("git checkout -f " + revision)

            version = reqLetter.getContent('vsn')
            version_date = reqLetter.getContent('datetime')

            building_cmds = building_cmds.replace("<vsn>", version)
            building_cmds = building_cmds.replace("datetime>", version_date)
            ret = os.system(building_cmds)

            with open(result_path, "rb") as result_file:
                vsn = reqLetter.getContent("vsn")
                needPost = reqletter.getHeader("needPost") # type: ignore
                target = server # type: Union[Server, Post]

                isNeedPost = needPost == 'true'

                if isNeedPost:
                    target = post

                for line in result_file:
                    extension = extensionFromPath(result_path) # type: ignore
                    binaryLetter = BinaryLetter(tid = vsn, bStr = line, # type:ignore
                                                extension = extension)
                    target.transfer(binaryLetter)

                if not isNeedPost:
                    response.setContent("state", Letter.RESPONSE_STATE_FINISHED)
                    server.transfer(response)
        except:
            response.setContent("state", Letter.RESPONSE_STATE_FAILURE)
            server.transfer(response)

    # Remove tasks from processor and return
    # the number of request finished
    def recyle(self) -> int:
        (readies, not_readies) = partition(self.__allTasks, lambda res: res[1].ready())
        self.__allTasks = not_readies

        for res in readies:
            del self.__allTasks_dict [res[0]]

        return len(readies)

    def isReqInProc(self, tid:str) -> bool:
        return tid in self.__allTasks_dict

    def isAbleToProc(self) -> bool:
        return self.tasksInProc() < self.maxTasksAbleToProc()

class Receiver(ModuleT):

    def __init__(self, server, info, cInst:Client) -> None:
        Thread.__init__(self)

        self.server = server
        self.max = int(info.getConfig('MAX_TASK_CAN_PROC'))
        self.numOfTasksInProc = 0
        self.pool = Pool( int(info.getConfig('PROCESS_POOL_SIZE')) )
        self.info = info

        self.inProcTasks = {} # type: Dict[str, Any]
        self.__status = 0

        self.__cInst = cInst

    def numOfTasks(self) -> int:
        return self.numOfTasksInProc

    def maxNumber(self) -> int:
        return self.max

    def stop(self) -> None:
        self.__status = 1

    def status(self) -> int:
        return self.__status

    def listOfTasks(self) -> List[Any]:
        return list( self.inProcTasks.values())

    def listOfTasks_ident(self) -> List[str]:
        return list( self.inProcTasks.keys())

    def run(self) -> None:

        server = self.server
        processor = self.__cInst.getModule('Processor')

        # Not Processor module
        if not isinstance(processor, Processor):
            raise Exception

        while True:

            if self.__status == 1:
                return None

            reqLetter = server.waitLetter()

            if isinstance(reqLetter, int):
                continue

            # print("Received letter:" + l.toString())

            processor.proc(reqLetter)
            processor.recyle()

class Post(Module):

    def __init__(self, address:str, port:int, info:Info, cInst:Client) -> None:
        self.__postHost = Server(address, port, info, cInst)


    def transfer(self, l:Letter) -> None:
        pass

class Server(Module):

    STATE_CONNECTED = 0
    STATE_CONNECTING = 1
    STATE_DISCONNECTED = 2

    SOCK_OK = 0
    SOCK_TIMEOUT = 1
    SOCK_DISCONN = 2

    def __init__(self, address:str, port:int, info:Info, cInst:Client) -> None:
        self.info = info

        queueSize = info.getConfig('QUEUE_SIZE')
        self.q = Manager().Queue(queueSize)

        # Lock to protect socket while reconnecting
        self.__lock = Manager().Lock()

        self.__address = address
        self.__port = port

        self.__status = Server.STATE_DISCONNECTED

    def connect(self, workerName:str, max:int, proc:int) -> State:
        # Store workerName into instance for reconnect purpose
        self.__workerName = workerName

        host = self.__address
        port = self.__port

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))

        self.sock.settimeout(1)

        propLetter = PropLetter(ident = workerName, max = str(max), proc = str(proc))
        if self.__send(propLetter) == Error:
            return Error

        self.__status = Server.STATE_CONNECTED
        return Ok

    def setSockTimeout(self, t) -> None:
        self.sock.settimeout(1)

    def disconnect(self) -> None:
        self.sock.shutdown(socket.SHUT_RDWR)
        self.sock.close()

        self.__status = Server.STATE_DISCONNECTED

    def waitLetter(self) -> Union[int, Letter]:
        return self.__recv(5)

    # Transfer a letter to server
    # calling of this method will not transfer
    # a letter to server instance instead the
    # letter will first buffer into a queue
    # and Sender will deal
    # with letters in queue
    def transfer(self, l) -> None:
        self.q.put(l)

    def transfer_step(self, timeout:int = None) -> int:
        response = self.q.get(timeout = timeout)
        return self.__send(response, retry = 3)

    def reconnectUntil(self, workerName:str, max:int, proc:int, timeout:int = None) -> State:
        ret = Error

        while ret == Error:
            ret = self.reconnect(workerName, max, proc)
            time.sleep(timeout) # type: ignore

        return ret

    def reconnect(self, workerName:str, max:int, proc:int) -> State:

        if workerName == "":
            workerName = self.__workerName

        try:
            return self.connect(workerName, max, proc)
        except:
            return Error

    def isResponseInQ(self) -> bool:
        return not self.q.empty()

    def __reconnectWrapper(self, retry:int = 0) -> int:
        time.sleep(3)

        with self.__lock:
            if self.__status != Server.STATE_DISCONNECTED:
                return Server.SOCK_OK


            if retry >= 0:
                while retry > 0:
                    ret = self.reconnect("", 0, 0)
                    if ret == Ok:
                        return Server.SOCK_OK
                    retry -= 1

                    # Retry interval is 5 seconds
                    time.sleep(5)

                return Server.SOCK_DISCONN
            else:
                self.reconnectUntil("", 0, 0, timeout = 5)
                return Server.SOCK_OK

    def __send(self, l:Letter, retry:int = 0) -> int:
        try:
            if isinstance(l, BinaryLetter):
                Server.__sending_bytes(self.sock, l.binaryPack()) # type: ignore
            else:
                Server.__sending(self.sock, l)
            return Server.SOCK_OK
        except socket.timeout:
            return Server.SOCK_TIMEOUT
        except:

            if self.__reconnectWrapper(retry) == Server.SOCK_OK:
                self.__send(l, retry)
                return Server.SOCK_OK

            return Server.SOCK_DISCONN

    def __send_bytes(self, b:bytes, retry:int = 0) -> int:
        try:
            Server.__sending_bytes(self.sock, b)
            return Server.SOCK_OK
        except socket.timeout:
            return Server.SOCK_TIMEOUT
        except:
            if self.__reconnectWrapper(retry) == Server.SOCK_OK:
                self.__send_bytes(b, retry)
                return Server.SOCK_OK

            return Server.SOCK_DISCONN

    def __recv(self, retry:int = 0) -> Union[int, Letter]:
        try:
            return Server.__receving(self.sock)
        except socket.timeout:
            return Server.SOCK_TIMEOUT
        except:
            if self.__reconnectWrapper(retry) == Server.SOCK_OK:
                return self.__recv(retry)
            return Server.SOCK_DISCONN

    @staticmethod
    def __receving(sock:socket.socket) -> Letter:
        content = b''
        remain = Letter.MAX_LEN

        while remain > 0:
            chunk = sock.recv(remain)
            if chunk == b'':
                raise DISCONN_EXCEPTION

            content += chunk
            remain = Letter.letterBytesRemain(content)

        return Letter.parse(content) # type: ignore

    @staticmethod
    def __sending(sock:socket.socket, l:Letter) -> None:
        jBytes = l.toBytesWithLength()
        return Server.__sending_bytes(sock, jBytes)

    @staticmethod
    def __sending_bytes(sock:socket.socket, bytesBuffer:bytes) -> None:
        totalSent = 0
        length = len(bytesBuffer)

        while totalSent < length:
            sent = sock.send(bytesBuffer[totalSent:])
            if sent == 0:
                raise DISCONN_EXCEPTION
            totalSent += sent

        return None


class Client(Thread):

    def __init__(self, mAddress:str, mPort:int, cfgPath:str, name:str = "") -> None:
        Thread.__init__(self)

        self.__cfgPath = cfgPath

        self.__name = name

        self.__mAddress = mAddress
        self.__mPort = mPort

        self.__status = 0
        self.__modules = {} # type: Dict[str, Module]

    def getIdent(self) -> str:
        return self.__name

    def stop(self) -> None:
        modules = list(self.__modules.values())
        for m in modules:
            if isinstance(m, ModuleT):
                m.stop()

    def inProcTasks(self) -> List[str]:
        taskDealer = self.getModule('Receiver')
        if not isinstance(taskDealer, Receiver):
            return []

        return taskDealer.listOfTasks_ident()

    def status(self) -> int:
        return self.__status

    def connect(self) -> None:
        server = self.getModule('Server')
        taskDealer = self.getModule('Receiver')

        if server is None or not isinstance(server, Server):
            return None
        if taskDealer is None or not isinstance(taskDealer, Receiver):
            return None

        server.connect(self.__name, taskDealer.maxNumber(), taskDealer.numOfTasks())

    def disconnect(self) -> None:
        server = self.getModule('Server')
        if server is None or not isinstance(server, Server):
            return None

        server.disconnect()

    def getModule(self, ident:str) -> Optional[Module]:
        if not ident in self.__modules:
            return None

        return self.__modules[ident]
    def addModules(self, ident:str, m:Module) -> None:
        if ident in self.__modules:
            return None

        self.__modules[ident] = m

    def run(self) -> None:
        info = Info(self.__cfgPath)

        address = self.__mAddress
        port = self.__mPort

        if self.__name == "":
            self.__name = workerName = info.getConfig('WORKER_NAME')
        else:
            workerName = self.__name

        max = info.getConfig('MAX_TASK_CAN_PROC')
        proc = info.getConfig('PROCESS_POOL_SIZE')

        s = Server(address, port, info, self)
        s.connect(workerName, max, proc)
        self.__modules['Server'] = s

        t1 = Receiver(s, info, self)
        self.__modules['Receiver'] = t1

        t2 = Sender(s, info, self)
        self.__modules['Sender'] = t2

        t3 = Recyler(self)
        self.__modules['Recyler'] = t3

        t4 = Post("127.0.0.1", 8013, info, self)
        self.__modules['Post'] = t4

        t5 = Processor(info, self)
        self.__modules['Processor']

        moduleThreads = list(
            filter(lambda m: isinstance(m, ModuleT), list(self.__modules.values()))
        )

        for m in moduleThreads:
            if isinstance(m, ModuleT):
                m.start()

        for m in moduleThreads:
            if isinstance(m, ModuleT):
                m.join()

        s.disconnect()
        self.__status = 1


if __name__ == '__main__':
    configPath = sys.argv[1]

    info = Info(configPath)

    address = info.getConfig('MASTER_ADDRESS', 'host')
    port = info.getConfig('MASTER_ADDRESS', 'port')

    client = Client(address, port, configPath)
    client.start()

    client.join()
