# server.py

import socket
import time
import platform

from ..basic.mmanager import Module

from ..basic.letter import Letter, PropLetter, BinaryLetter, ResponseLetter, \
    receving as letter_receving, sending as letter_sending
from ..basic.info import Info, M_NAME as INFO_M_NAME
from ..basic.type import *
from ..basic.util import sockKeepalive

from typing import Any, Union, Optional
from threading import Lock
from queue import Queue, Empty

M_NAME = "Server"

class DISCONN_EXCEPTION(Exception):
    pass

class Server(Module):

    STATE_SUSPEND = 4
    STATE_CONNECTED = 0
    STATE_CONNECTING = 1
    STATE_DISCONNECTED = 2
    STATE_TRANSFER = 3

    SOCK_OK = 0
    SOCK_TIMEOUT = 1
    SOCK_DISCONN = 2
    SOCK_PARSE_ERROR = 3

    def __init__(self, address:str, port:int, info:Info, cInst:Any) -> None:
        global M_NAME

        Module.__init__(self, M_NAME)
        self.info = info

        queueSize = info.getConfig('QUEUE_SIZE')
        self.q = Queue(queueSize) # type: Queue[ResponseLetter]

        # Lock to protect socket while reconnecting
        self.__lock = Lock()

        self.__address = address
        self.__port = port

        self.__max = 0
        self.__proc = 0

        self.__status = Server.STATE_SUSPEND

        # A flag to indicate this connection to master
        # should be closed and never rebuild in the future.
        self.__isStop = False

        self.__cInst = cInst

    def getStatus(self) -> int:
        return self.__status

    def setStatus(self, status:int) -> None:
        self.__status = status

    def setWorkerName(self, name:str) -> None:
        self.__workerName = name

    def cleanup(self) -> None:
        self.__isStop = True
        self.disconnect()

    def begin(self) -> None:
        self.connect()

    def connect(self) -> State:
        info = self.__cInst.getModule(INFO_M_NAME)

        self.__proc = self.__cInst.inProcTasks()
        if self.__proc is None:
            self.__proc = 0

        self.__max = info.getConfig('MAX_TASK_CAN_PROC')

        return self._connect(self.__max, self.__proc)

    def _connect(self, max:int, proc:int, retry:int = 0) -> State:

        if self.__isStop: return Error

        host = self.__address
        port = self.__port

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sockKeepalive(sock, 10, 3)

        retry += 1

        while retry > 0:
            retry -= 1

            try:
                sock.connect((host, port))
                break

            except ConnectionRefusedError:
                if retry > 0:
                    continue
                else:
                    sock.close()
                    return Error
            except:
                sock.close()
                return Error

        sock.settimeout(1)

        propLetter = PropLetter(ident = self.__workerName,
                                max = str(max),
                                proc = str(proc))
        if self.__sending(sock, propLetter) == Error:
            return Error

        self.sock = sock
        self.__status = Server.STATE_CONNECTED

        return Ok

    def setSockTimeout(self, t:int) -> None:
        self.sock.settimeout(1)

    def disconnect(self) -> None:
        if hasattr(self, 'sock'):
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

    def transfer_step(self, timeout:int = None) -> State:

        # Server module is in stop state.
        # Not allow to transfer messages until authorized by master
        if self.__isStop or self.__status != Server.STATE_TRANSFER:
            return Error

        try:
            response = self.q.get_nowait()
        except Empty:
            return Error

        if self.__send(response, retry = 1) == Server.SOCK_OK:
            return Ok
        else:
            # Insert into head of the queue
            self.q.queue.insert(0, response)

        return Error

    def drop_all_messages(self) -> None:
        self.q.queue.clear()

    def responseRetrive(self) -> Optional[Letter]:
        try:
            return self.q.get(timeout = 1)
        except:
            return None

    def reconnectUntil(self, interval:int = None) -> State:
        ret = Error

        while ret == Error:
            ret = self.reconnect()
            time.sleep(interval) # type: ignore

        return ret

    def reconnect(self) -> State:
        if self.__status != Server.STATE_DISCONNECTED:
            return Error

        try:
            return self.connect()
        except:
            return Error

    def isResponseInQ(self) -> bool:
        return not self.q.empty()

    def __reconnectWrapper(self, retry:int = 0) -> int:
        with self.__lock:
            if self.__status != Server.STATE_DISCONNECTED:
                return Server.SOCK_OK

            if retry >= 0:
                while retry > 0:
                    ret = self.reconnect()
                    if ret == Ok:
                        return Server.SOCK_OK
                    retry -= 1

                    # Retry interval is 5 seconds
                    time.sleep(5)

                return Server.SOCK_DISCONN
            else:
                self.reconnectUntil(interval = 1)
                return Server.SOCK_OK

    def __send(self, l:Letter, retry:int = 0) -> int:

        while True:
            try:
                if isinstance(l, BinaryLetter):
                    Server.__sending_bytes(self.sock, l.binaryPack()) # type: ignore
                else:
                    Server.__sending(self.sock, l)
                return Server.SOCK_OK
            except socket.timeout:
                return Server.SOCK_TIMEOUT
            except BinaryLetter.FIELD_LENGTH_EXCEPTION:
                return Server.SOCK_PARSE_ERROR
            except:
                self.__status = Server.STATE_DISCONNECTED
                if self.__reconnectWrapper(retry) == Server.SOCK_OK:
                    continue
                else:
                    return Server.SOCK_DISCONN

            return Server.SOCK_OK

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

        while True:
            try:
                letter = Server.__receving(self.sock)
                if letter is None:
                    return Server.SOCK_PARSE_ERROR
                return letter

            except socket.timeout:
                return Server.SOCK_TIMEOUT

            except:
                self.__status = Server.STATE_DISCONNECTED
                if self.__reconnectWrapper(retry) == Server.SOCK_OK:
                    continue
                return Server.SOCK_DISCONN

    @staticmethod
    def __receving(sock:socket.socket) -> Optional[Letter]:
        return letter_receving(sock)

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
