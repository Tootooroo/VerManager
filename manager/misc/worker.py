# worker.py
#
# Maintain connection with workers and
# provide communication interface to another module

import socket
import typing
import select

from .task import *
from datetime import datetime, timedelta

from functools import reduce
from threading import Thread, Lock

from manager.misc.basic.letter import Letter
from manager.misc.basic.type import Ok, Error

class WorkerInitFailed(Exception):
    pass

WorkerState = int

class Worker(socket.socket):

    STATE_ONLINE = 0
    STATE_WAITING = 1
    STATE_OFFLINE = 2

    def __init__(self, sock: socket.socket) -> None:
        self.sock = sock
        self.max = 0
        self.processing = 0
        self.inProcTask = TaskGroup()
        self.ident = ""

        # TaskGroup is not a thread safe object
        # lock should protect TaskGroup and processing
        self.lock = Lock()

        # Before a PropertyNotify letter is report
        # from worker we see a worker as an offline
        # worker
        self.state = Worker.STATE_OFFLINE

        # Counters
        # 1.wait_counter: ther number of seconds that a worker stay in STATE_WAITING
        # 2.offline_counter: the number of seconds that a worker stay in STATE_OFFLINE
        # 3.online_counter: the number of seconds that a worker stay in STATE_ONLINE
        # 4.clock: Record the time while state of Worker is changed and counter 1 to 3
        #          is calculated via clock. Clock is not accessable by user directly.
        #
        # counters[STATE_ONLINE] : online_counter
        # counters[STATE_WAITING] : wait_counter
        # counters[STATE_OFFLINE] : offline_counter
        self.counters = [0, 0, 0]
        self.__clock = datetime.now()

        # Prevent permanent blocking from waiting for PropertyNotify from worker
        self.sock.settimeout(10)

        # Worker is created while a connection is created between
        # worker and server. The first letter from worker to server
        # must a PropertyNotify type
        try:
            l = self.__recv()

            # May happen if messages from worker is not valid
            if l is None:
                raise WorkerInitFailed()

        except socket.timeout:
            raise WorkerInitFailed()

        # After PropertyNotify is received reset timeout value to default
        self.sock.settimeout(None)

        if Letter.typeOfLetter(l) == Letter.PropertyNotify:
            self.max = l.propNotify_MAX()
            self.processing = l.propNotify_PROC()
            self.ident = l.propNotify_IDENT()
            self.state = Worker.STATE_ONLINE
            self.__clock = datetime.utcnow()
        else:
            raise Exception

    def sockSet(self, sock: socket.socket) -> None:
        self.sock = sock

    def sockGet(self) -> socket.socket:
        return self.sock

    def waitCounter(self) -> int:
        return self.counters[Worker.STATE_WAITING]

    def offlineCounter(self) -> int:
        return self.counters[Worker.STATE_OFFLINE]

    def onlineCounter(self) -> int:
        return self.counters[Worker.STATE_ONLINE]

    def counterSync(self) -> None:
        delta = datetime.utcnow() - self.__clock
        self.counters[self.state] = delta.seconds

    def setState(self, s: WorkerState) -> None:
        if self.state != s:
            self.counters[self.state] = 0

        self.state = s
        self.__clock = datetime.utcnow()

    def getIdent(self) -> str:
        return self.ident

    def isOnline(self) -> bool:
        return self.state == Worker.STATE_ONLINE

    def isWaiting(self) -> bool:
        return self.state == Worker.STATE_WAITING

    def isOffline(self) -> bool:
        return self.state == Worker.STATE_OFFLINE

    def isFree(self) -> bool:
        return self.processing == 0

    def isAbleToAccept(self) -> bool:
        return self.processing < self.max

    def searchTask(self, tid: str) -> Optional[Task]:
        with self.lock:
            return self.inProcTask.search(tid)

    def removeTask(self, tid: str) -> None:
        with self.lock:
            self.processing -= 1
            self.inProcTask.remove(tid)

    def numOfTaskProc(self) -> int:
        return self.processing

    def do(self, task: Task) -> None:
        if not self.isAbleToAccept():
            raise Exception

        # Task assign
        letter = Letter(Letter.NewTask, {"ident":self.ident, "tid":task.id()}, \
                        task.content)
        self.__send(letter)

        # Register task into task group
        task.stateChange(Task.STATE_IN_PROC)

        with self.lock:
            self.processing += 1
            self.inProcTask.newTask(task)

    # Provide ability to cancel task in queue or
    # processed task
    # Note: sn here should be a version sn
    def cancel(self, id: str) -> str:
        pass

    # fixme: should support binary letter
    def receving(sock: socket.socket) -> Optional[Letter]:
        content = b''
        remain = Letter.BINARY_HEADER_LEN

        while remain > 0:
            chunk = sock.recv(remain)
            if chunk == b'':
                raise Exception

            content += chunk
            remain = Letter.letterBytesRemain(content)

        return Letter.parse(content)

    def sending(sock: socket.socket, l: Letter) -> None:
        jBytes = l.toBytesWithLength()
        totalSent = 0
        length = len(jBytes)

        while totalSent < length:
            sent = sock.send(jBytes[totalSent:])
            if sent == 0:
                raise Exception
            totalSent += sent

    def __recv(self) -> Optional[Letter]:
        return Worker.receving(self.sock)

    def __send(self, l: Letter) -> None:
        Worker.sending(self.sock, l)
