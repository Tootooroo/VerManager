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

from .basic.letter import *
from .basic.info import Info
from .basic.type import *

from multiprocessing import Pool, Queue, Manager
from threading import Thread, Condition

class DISCONN_EXCEPTION(Exception):
    pass

class StopableThread(Thread):

    def stop(self) -> None:
        pass

class RESPONSE_TO_SERVER_DAEMON(StopableThread):

    def __init__(self, server, info) -> None:
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
                # Waiting for <TASK_DEAL_DAEMON> reconnecting
                time.sleep(5)
                continue

class TASK_COUNTER_MAINTAIN(StopableThread):

    def __init__(self, t) -> None:
        Thread.__init__(self)
        self.tasks = t.inProcTasks
        self.t = t

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

            for task in self.tasks:
                if task.ready() == True:
                    self.t.numOfTasksInProc -= 1

            time.sleep(0.05)


class TASK_DEAL_DAEMON(StopableThread):

    def __init__(self, server, info) -> None:
        Thread.__init__(self)

        self.server = server
        self.max = int(info.getConfig('MAX_TASK_CAN_PROC'))
        self.numOfTasksInProc = 0
        self.pool = Pool( int(info.getConfig('PROCESS_POOL_SIZE')) )
        self.info = info

        self.inProcTasks = [] # type: ignore

        self.__status = 0

    def numOfTasks(self) -> int:
        return self.numOfTasksInProc

    def maxNumber(self) -> int:
        return self.max

    def stop(self) -> None:
        self.__status = 1

    def status(self) -> int:
        return self.__status

    def run(self) -> None:

        WORKER_NAME = self.info.getConfig('WORKER_NAME')
        server = self.server

        # Spawn TASK_COUNTER_MAINTAIN Thread
        counter_maintainer = TASK_COUNTER_MAINTAIN(self)
        counter_maintainer.start()

        while True:

            if self.__status == 1:
                counter_maintainer.stop()
                return None

            l = server.waitLetter()

            if isinstance(l, int):
                continue

            print("Received letter:" + l.toString())

            if not self.numOfTasksInProc < self.max:
                # Worker is unable to accept task
                # just response failure to server
                letter = ResponseLetter(
                    ident = WORKER_NAME,
                    state = Letter.RESPONSE_STATE_FAILURE,
                    tid = l.getContent('vsn'))
                server.transfer(letter)
                continue

            self.numOfTasksInProc += 1
            res = self.pool.apply_async(TASK_DEAL_DAEMON.job, (server, l, self.info))

            self.inProcTasks.append(res)

    # Processing the assigned task and send back the result to server
    @staticmethod
    def job(server: 'Server', letter: typing.Any, info: Info) -> None:

        REPO_URL = info.getConfig('REPO_URL')
        PROJECT_NAME = info.getConfig('PROJECT_NAME')
        WORKER_NAME = info.getConfig('WORKER_NAME')
        BUILDING_CMDS = info.getConfig('BUILDING_CMDS')
        RESULT_PATH = info.getConfig('RESULT_PATH')

        if platform.system() == 'Windows':
            RESULT_PATH = RESULT_PATH.replace("/", "\\")
            BUILDING_CMDS = "&&".join(list(map(lambda cmd: cmd.replace("/", "\\"), BUILDING_CMDS)))
        else:
            # Linux platform
            BUILDING_CMDS = ";".join(BUILDING_CMDS)

        # Notify to server the worker is in processing
        letterInProc = ResponseLetter(
            ident = WORKER_NAME,
            tid = letter.getContent('vsn'),
            state = Letter.RESPONSE_STATE_IN_PROC)
        server.transfer(letterInProc)

        revision = letter.getContent('sn')
        vsn = letter.getContent('vsn')
        vsn_date = letter.getContent('datetime')

        # Replace <vsn> and <sn> with value from server
        BUILDING_CMDS = BUILDING_CMDS.replace("<vsn>", vsn)
        BUILDING_CMDS = BUILDING_CMDS.replace("<datetime>", vsn_date)

        # Processing
        try:
            # Fetch
            ret = os.system("git clone -b master " + REPO_URL)

            os.chdir(PROJECT_NAME)

            # Revision checkout
            ret = os.system("git checkout -f " + revision)

            # Building
            ret = os.system(BUILDING_CMDS)

            # Send back to server
            with open(RESULT_PATH, 'rb') as file:
                for line in file:
                    binaryLetter = BinaryLetter(tid = vsn, bStr = line)
                    server.transfer(binaryLetter)

            # Response to server to notify that the task is finished
            finishedLetter = ResponseLetter(ident = WORKER_NAME, tid = vsn,
                                            state = Letter.RESPONSE_STATE_FINISHED)
            server.transfer(finishedLetter)

            # os.chdir("..")
            # ret = os.system("rm", "-rf", PROJECT_NAME)

        except:
            traceback.print_exc()
            letter = ResponseLetter(ident = WORKER_NAME, tid = vsn,
                                    state = Letter.RESPONSE_STATE_FAILURE)
            server.transfer(letter)
            return None

class Server:

    STATE_CONNECTED = 0
    STATE_CONNECTING = 1
    STATE_DISCONNECTED = 2

    SOCK_OK = 0
    SOCK_TIMEOUT = 1
    SOCK_DISCONN = 2

    def __init__(self, address:str, port:int, info:Info) -> None:
        self.info = info

        queueSize = int(info.getConfig('QUEUE_SIZE'))
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
    # and RESPONSE_TO_SERVER_DAEMON will deal
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
            time.sleep(timeout)

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

            print("Reconnect")

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
                Server.__sending_bytes(self.sock, l.binaryPack())
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

        return Letter.parse(content)

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
        self.__modules = [] # type: List[Any]

    def stop(self) -> None:
        for m in self.__modules:
            if isinstance(m, StopableThread):
                m.stop()

    def status(self) -> int:
        return self.__status

    def connect(self) -> None:
        s = list( filter(lambda m: isinstance(m, Server), self.__modules))
        s1 = list( filter(lambda m: isinstance(m, TASK_DEAL_DAEMON), self.__modules))

        if s == [] or len(s) > 1:
            return None

        if s1 == [] or len(s1) > 1:
            return None

        server = s[0]
        taskDealer = s1[0]

        server.connect(self.__name, taskDealer.maxNumber(), taskDealer.numOfTasks)


    def disconnect(self) -> None:
        s = list( filter(lambda m: isinstance(m, Server), self.__modules))
        if s == [] or len(s) > 1:
            return None

        server = s[0]

        server.disconnect()


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

        s = Server(address, port, info)
        s.connect(workerName, int(max), int(proc))
        self.__modules.append(s)

        t1 = TASK_DEAL_DAEMON(s, info)
        self.__modules.append(t1)

        t2 = RESPONSE_TO_SERVER_DAEMON(s, info)
        self.__modules.append(t2)

        for m in self.__modules:
            if isinstance(m, Thread):
                m.start()

        for m in self.__modules:
            if isinstance(m, Thread):
                m.join()

        s.disconnect()
        self.__status = 1

        print("Client Stop")


if __name__ == '__main__':
    configPath = sys.argv[1]

    info = Info(configPath)

    address = info.getConfig('MASTER_ADDRESS', 'host')
    port = int(info.getConfig('MASTER_ADDRESS', 'port'))

    client = Client(address, port, configPath)
    client.start()

    client.join()
