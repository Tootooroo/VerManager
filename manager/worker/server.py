# server.py

import socket
import time

from ..basic.mmanager import Module

from ..basic.letter import Letter, PropLetter, BinaryLetter, ResponseLetter, \
    receving as letter_receving, LogRegLetter, LogLetter, \
    CmdResponseLetter
from ..basic.info import Info, M_NAME as INFO_M_NAME
from ..basic.type import State, Ok, Error
from ..basic.util import sockKeepalive
from .type import SEND_STATES, SEND_STATE

from typing import Any, Union, Optional, Dict
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

    def __init__(self, address: str, port: int,
                 info: Info, cInst: Any) -> None:

        global M_NAME

        Module.__init__(self, M_NAME)
        self.info = info

        queueSize = info.getConfig('QUEUE_SIZE')
        self.q = Queue(queueSize)  # type: Queue[ResponseLetter]

        # Lock to protect socket while reconnecting
        self._lock = Lock()

        self._address = address
        self._port = port

        self._max = 0
        self._proc = 0

        self._status = Server.STATE_SUSPEND

        # A flag to indicate this connection to master
        # should be closed and never rebuild in the future.
        self._isStop = False

        self._cInst = cInst

    def getStatus(self) -> int:
        return self._status

    def setStatus(self, status: int) -> None:
        self._status = status

    def setWorkerName(self, name: str) -> None:
        self._workerName = name

    def cleanup(self) -> None:
        self._isStop = True
        self.disconnect()

    def begin(self) -> None:
        self.connect()

    def connect(self) -> State:
        info = self._cInst.getModule(INFO_M_NAME)

        self._proc = self._cInst.inProcTasks()
        if self._proc is None:
            self._proc = 0

        self._max = info.getConfig('MAX_TASK_CAN_PROC')

        return self._connect(self._max, self._proc)

    def _connect(self, max: int, proc: int, retry: int = 0) -> State:

        if self._isStop:
            return Error

        host = self._address
        port = self._port

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
            except Exception:
                sock.close()
                return Error

        sock.settimeout(1)

        propLetter = PropLetter(ident=self._workerName,
                                max=str(max),
                                proc=str(proc))

        try:
            self._sending(sock, propLetter)
        except Exception:
            return Error

        self.sock = sock
        self._status = Server.STATE_CONNECTED

        return Ok

    def setSockTimeout(self, t: int) -> None:
        self.sock.settimeout(1)

    def disconnect(self) -> None:
        if hasattr(self, 'sock'):
            self.sock.shutdown(socket.SHUT_RDWR)
            self.sock.close()

        self._status = Server.STATE_DISCONNECTED

    def _response_task_state(self, tid: str, state: str) -> None:
        response = ResponseLetter(self._cInst.getIdent(), tid, state)
        self.transfer(response)

    def response_in_proc(self, tid: str) -> None:
        self._response_task_state(tid, Letter.RESPONSE_STATE_IN_PROC)

    def response_fin(self, tid: str) -> None:
        self._response_task_state(tid, Letter.RESPONSE_STATE_FINISHED)

    def response_failure(self, tid: str) -> None:
        self._response_task_state(tid, Letter.RESPONSE_STATE_FAILURE)

    def control_response(self, cmd_type: str, state: str,
                         extra: Dict[str, str]) -> None:

        cmd_response = CmdResponseLetter(self._cInst.getIdent(),
                                         cmd_type, state, extra)
        self.transfer(cmd_response)

    def bytesSend(self, l: BinaryLetter) -> None:
        self.transfer(l)

    def log_register(self, id: str) -> None:
        regLetter = LogRegLetter(self._cInst.getIdent(), id)
        self.transfer(regLetter)

    def log(self, id: str, msg: str) -> None:
        logLetter = LogLetter(self._cInst.getIdent(), id, msg)
        self.transfer(logLetter)

    def waitLetter(self) -> Union[int, Letter]:
        return self._recv(5)

    # Transfer a letter to server
    # calling of this method will not transfer
    # a letter to server instance instead the
    # letter will first buffer into a queue
    # and Sender will deal
    # with letters in queue
    def transfer(self, l) -> None:
        self.q.put(l)

    def transfer_step(self, timeout: int = None) -> SEND_STATE:

        # Server module is in stop state.
        # Not allow to transfer messages until authorized by master
        if self._isStop or self._status != Server.STATE_TRANSFER:
            return SEND_STATES.UNAVAILABLE

        try:
            response = self.q.get_nowait()
        except Empty:
            return SEND_STATES.NO_DATA

        if self._send(response, retry=1) == Server.SOCK_OK:
            return SEND_STATES.DATA_SENDED
        else:
            # Insert into head of the queue
            self.q.queue.insert(0, response)  # type:  ignore

        return SEND_STATES.UNAVAILABLE

    def drop_all_messages(self) -> None:
        self.q.queue.clear()  # type:  ignore

    def responseRetrive(self) -> Optional[Letter]:
        try:
            return self.q.get(timeout=1)
        except Exception:
            return None

    def reconnectUntil(self, interval: int = None) -> State:
        ret = Error

        while ret == Error:
            ret = self.reconnect()
            time.sleep(interval)  # type:  ignore

        return ret

    def reconnect(self) -> State:
        if self._status != Server.STATE_DISCONNECTED:
            return Error

        try:
            return self.connect()
        except Exception:
            return Error

    def isResponseInQ(self) -> bool:
        return not self.q.empty()

    def _reconnectWrapper(self, retry: int = 0) -> int:
        with self._lock:
            if self._status != Server.STATE_DISCONNECTED:
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
                self.reconnectUntil(interval=1)
                return Server.SOCK_OK

    def _send(self, l: Letter, retry: int = 0) -> int:

        while True:
            try:
                if isinstance(l, BinaryLetter):
                    letter_bytes = l.binaryPack()
                    assert(letter_bytes is not None)

                    Server._sending_bytes(self.sock, letter_bytes)
                else:
                    Server._sending(self.sock, l)
                return Server.SOCK_OK
            except socket.timeout:
                return Server.SOCK_TIMEOUT
            except BinaryLetter.FIELD_LENGTH_EXCEPTION:
                return Server.SOCK_PARSE_ERROR
            except Exception:
                self._status = Server.STATE_DISCONNECTED
                if self._reconnectWrapper(retry) == Server.SOCK_OK:
                    continue
                else:
                    return Server.SOCK_DISCONN

            return Server.SOCK_OK

    def _send_bytes(self, b: bytes, retry: int = 0) -> int:
        try:
            Server._sending_bytes(self.sock, b)
            return Server.SOCK_OK
        except socket.timeout:
            return Server.SOCK_TIMEOUT
        except Exception:
            if self._reconnectWrapper(retry) == Server.SOCK_OK:
                self._send_bytes(b, retry)
                return Server.SOCK_OK

            return Server.SOCK_DISCONN

    def _recv(self, retry: int = 0) -> Union[int, Letter]:

        while True:
            try:
                letter = Server._receving(self.sock)
                if letter is None:
                    return Server.SOCK_PARSE_ERROR
                return letter

            except socket.timeout:
                return Server.SOCK_TIMEOUT

            except Exception:
                self._status = Server.STATE_DISCONNECTED
                if self._reconnectWrapper(retry) == Server.SOCK_OK:
                    continue
                return Server.SOCK_DISCONN

    @staticmethod
    def _receving(sock: socket.socket) -> Optional[Letter]:
        return letter_receving(sock)

    @staticmethod
    def _sending(sock: socket.socket, l: Letter) -> None:
        jBytes = l.toBytesWithLength()
        return Server._sending_bytes(sock, jBytes)

    @staticmethod
    def _sending_bytes(sock: socket.socket, bytesBuffer: bytes) -> None:
        totalSent = 0
        length = len(bytesBuffer)

        while totalSent < length:
            sent = sock.send(bytesBuffer[totalSent:])
            if sent == 0:
                raise DISCONN_EXCEPTION
            totalSent += sent
