# MIT License
#
# Copyright (c) 2020 Gcom
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# server.py

import time
import asyncio

from ..basic.mmanager import Module

from ..basic.letter import Letter, PropLetter, BinaryLetter, ResponseLetter, \
    receving as letter_receving, LogRegLetter, LogLetter, \
    CmdResponseLetter
from ..basic.info import Info
from ..basic.type import State, Ok, Error
from .type import SEND_STATES, SEND_STATE

from typing import Union, Optional, Dict

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

    def __init__(self, address: str, port: int, info: Info) -> None:

        global M_NAME

        Module.__init__(self, M_NAME)

        self.q = asyncio.Queue(
            info.getConfig('QUEUE_SIZE')
        )  # type: asyncio.Queue[ResponseLetter]

        # Lock to protect socket while reconnecting
        self._lock = asyncio.Lock()

        self._address = address
        self._port = port

        self._workerName = ""
        self._max = 0
        self._proc = 0

        self._status = Server.STATE_SUSPEND

        # A flag to indicate this connection to master
        # should be closed and never rebuild in the future.
        self._isStop = False

        self._reader = None  # type: Optional[asyncio.StreamReader]
        self._writer = None  # type: Optional[asyncio.StreamWriter]

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

    async def connect(self) -> State:
        return await self._connect(self._max, self._proc)

    async def _connect(self, max: int, proc: int, retry: int = 0) -> State:
        host = self._address
        port = self._port

        while retry >= 0:
            try:
                self._reader, self._writer = \
                    await asyncio.open_connection(host, port)
                break
            except Exception as e:
                print(e)
                return Error

            retry -= 1

        if self._reader is None or self._writer is None:
            return Error

        propLetter = PropLetter(
            ident=self._workerName, max=str(max), proc=str(proc))

        try:
            self._send(propLetter)
        except Exception as e:
            print(e)
            return Error

        self._status = Server.STATE_CONNECTED
        return Ok

    def disconnect(self) -> None:
        if self._writer is not None:
            self._writer.close()
            self._status = Server.STATE_DISCONNECTED

    def _response_task_state(self, tid: str, state: str) -> None:
        response = ResponseLetter(self._workerName, tid, state)
        self.transfer(response)

    def response_in_proc(self, tid: str) -> None:
        self._response_task_state(tid, Letter.RESPONSE_STATE_IN_PROC)

    def response_fin(self, tid: str) -> None:
        self._response_task_state(tid, Letter.RESPONSE_STATE_FINISHED)

    def response_failure(self, tid: str) -> None:
        self._response_task_state(tid, Letter.RESPONSE_STATE_FAILURE)

    def control_response(self, cmd_type: str, state: str,
                         extra: Dict[str, str]) -> None:

        cmd_response = CmdResponseLetter(
            self._workerName, cmd_type, state, extra)
        self.transfer(cmd_response)

    def bytesSend(self, letter: BinaryLetter) -> None:
        self.transfer(letter)

    def log_register(self, id: str) -> None:
        regLetter = LogRegLetter(self._workerName, id)
        self.transfer(regLetter)

    def log(self, id: str, msg: str) -> None:
        logLetter = LogLetter(self._workerName, id, msg)
        self.transfer(logLetter)

    def waitLetter(self) -> Union[int, Letter]:
        return self._recv(5)

    # Transfer a letter to server
    # calling of this method will not transfer
    # a letter to server instance instead the
    # letter will first buffer into a queue
    # and Sender will deal
    # with letters in queue
    def transfer(self, letter) -> None:
        self.q.put(letter)

    def transfer_step(self, timeout: int = None) -> SEND_STATE:

        # Server module is in stop state.
        # Not allow to transfer messages until authorized by master
        if self._isStop or self._status != Server.STATE_TRANSFER:
            return SEND_STATES.UNAVAILABLE

        response = self.q.get_nowait()

        if self._send(response, retry=1) == Server.SOCK_OK:
            return SEND_STATES.DATA_SENDED
        else:
            # Insert into head of the queue
            self.q.queue.insert(0, response)  # type:  ignore

        return SEND_STATES.UNAVAILABLE

    async def drop_all_messages(self) -> None:
        await self.q.queue.clear()  # type:  ignore

    async def responseRetrive(self, timeout=None) -> Optional[Letter]:
        try:
            return await asyncio.wait_for(
                self.q.get(), timeout=timeout)
        except asyncio.exceptions.TimeoutError:
            return None

    async def reconnectUntil(self, interval: int = 1) -> State:
        ret = Error

        while ret == Error:
            ret = await self.reconnect()
            await asyncio.sleep(interval)  # type:  ignore

        return ret

    async def reconnect(self) -> State:
        if self._status != Server.STATE_DISCONNECTED:
            return Error

        try:
            return self.connect()
        except Exception:
            return Error

    def isResponseInQ(self) -> bool:
        return not self.q.empty()

    async def _reconnectWrapper(self, retry: int = 0) -> int:
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

    def _send(self, letter: Letter, retry: int = 0) -> int:
        jBytes = letter.toBytesWithLength()

        if self._writer is None:
            return Error

        Server._sending(self._writer, jBytes)
        return Ok

    def _send_bytes(self, b: bytes) -> int:
        if self._writer is None:
            return Error
        Server._sending(self._writer, b)
        return Ok

    async def _recv(self, retry: int = 0) -> Union[int, Letter]:
        if self._reader is None:
            return Error
        return await Server._receving(self._reader)

    @staticmethod
    async def _receving(reader: asyncio.StreamReader) -> Optional[Letter]:
        return await letter_receving(reader)

    @staticmethod
    def _sending(writer: asyncio.StreamWriter, bytesBuffer: bytes) -> None:
        writer.write(bytesBuffer)
