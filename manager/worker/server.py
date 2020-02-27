# server.py

import socket
import time

from ..basic.mmanager import Module

from ..basic.letter import Letter, PropLetter, BinaryLetter
from ..basic.info import Info
from ..basic.type import *

from typing import Any, Union, Optional
from multiprocessing import Manager

class DISCONN_EXCEPTION(Exception):
    pass

class Server(Module):

    STATE_CONNECTED = 0
    STATE_CONNECTING = 1
    STATE_DISCONNECTED = 2

    SOCK_OK = 0
    SOCK_TIMEOUT = 1
    SOCK_DISCONN = 2

    def __init__(self, address:str, port:int, info:Info, cInst:Any) -> None:
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

    def setSockTimeout(self, t:int) -> None:
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

    def responseRetrive(self) -> Optional[Letter]:
        try:
            return self.q.get(timeout = 1)
        except:
            return None

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
