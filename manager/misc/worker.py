# worker.py
#
# Maintain connection with workers and
# provide communication interface to another module

import socket

from multiprocessing import Process
from manager.misc.letter import Letter

class Worker:

    STATE_PREPARE = 0
    STATE_READY = 1
    STATE_WAIT_RESPONSE = 2

    def __init__(self, sock: socket.Socket):
        self.sock = sock
        self.max = 0
        self.processing = 0
        self.state = STATE_PREPARE
        self.inProcTask = []

        l = self.__recv()
        if Letter.typeOfLetter(l) == Letter.PropertyNotify:
            self.max = l.propNotify_MAX()
            self.processing = l.propNotify_PROC()
        else:
            raise Exception

    def isFree(self) -> bool:
        self.processing == 0

    def isAbletoAccept(self) -> bool:
        self.processing < self.max

    def do(self, content: T) -> None:
        if not self.isAbleToAccept():
            raise Exception

        # Do task assign
        do_letter = Letter(Letter.NewTask, content)
        self.__send(do_letter)

        self.state = STATE_WAIT_RESPONSE

    # Provide ability to cancel task in queue or
    # processed task
    # Note: sn here should be a version sn
    def cancel(self, sn: Str):
        if self.isFree:
            raise Exception

        cancel_letter = Letter(Letter.TaskCancel, {"sn":sn})
        self.sock.send(cancel_letter.toJson())

    def __recv(self) -> Letter:
        content = None
        received = 0
        MAX_LEN = Letter.MAX_LEN

        content = self.sock.recv(Letter.MAX_LEN)
        if content == b'':
            raise Exception
        elif content[0] != '{':
            # Fragmentation, need to call recv
            # several times
            end = chunk.find('{')
            MAX_LEN = int(chunk[:end])
            received = len(chunk) - end

            while received < MAX_LEN:
                chunk = self.sock.recv(MAX_LEN - received)
                if chunk == b'':
                    raise Exception
                received += len(chunk)
                content += chunk

            return acc

        return json2Letter(content)

    def __send(self, l: Letter) -> None:
        jStr = l.toJson()
        totalSent = 0
        length = len(jStr)

        while totalSent < length:
            sent = self.sock.send(jStr[totalSent:])
            if sent == 0:
                raise Exception
            totalSent += sent

