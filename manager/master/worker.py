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

from manager.basic.letter import Letter, NewLetter
from manager.basic.type import Ok, Error
from manager.basic.commands import Command

class WorkerInitFailed(Exception):
    pass

WorkerState = int

class Worker:

    STATE_ONLINE = 0
    STATE_WAITING = 1
    STATE_OFFLINE = 2

    def __init__(self, sock: socket.socket, address:Tuple[str, int]) -> None:
        self.sock = sock
        self.address = address
        self.max = 0
        self.inProcTask = TaskGroup()
        self.ident = ""

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

    def active(self) -> None:
        # Prevent permanent blocking from waiting for PropertyNotify from worker
        self.sock.settimeout(10)

        try:
            l = self.__recv()

            if l is None:
                raise WorkerInitFailed()

        except socket.timeout:
            raise WorkerInitFailed()

        self.sock.settimeout(None)

        if Letter.typeOfLetter(l) == Letter.PropertyNotify:
            self.max = l.propNotify_MAX()
            self.ident = l.propNotify_IDENT()
            self.state = Worker.STATE_ONLINE
            self.__clock = datetime.utcnow()
        else:
            raise WorkerInitFailed()

    def sockSet(self, sock: socket.socket) -> None:
        self.sock = sock

    def sockGet(self) -> socket.socket:
        return self.sock

    def waitCounter(self) -> int:
        self.__counterSync()
        return self.counters[Worker.STATE_WAITING]

    def offlineCounter(self) -> int:
        self.__counterSync()
        return self.counters[Worker.STATE_OFFLINE]

    def onlineCounter(self) -> int:
        self.__counterSync()
        return self.counters[Worker.STATE_ONLINE]

    def __counterSync(self) -> None:
        delta = datetime.utcnow() - self.__clock
        self.counters[self.state] = delta.seconds

    def setState(self, s: WorkerState) -> None:
        if self.state != s:
            self.counters[self.state] = 0

        self.state = s
        self.__clock = datetime.utcnow()

    def getAddress(self) -> Tuple[str, int]:
        return self.address

    def getIdent(self) -> str:
        return self.ident

    def isOnline(self) -> bool:
        return self.state == Worker.STATE_ONLINE

    def isWaiting(self) -> bool:
        return self.state == Worker.STATE_WAITING

    def isOffline(self) -> bool:
        return self.state == Worker.STATE_OFFLINE

    def isFree(self) -> bool:
        return self.inProcTask.numOfTasks() == 0

    def isAbleToAccept(self) -> bool:
        return self.inProcTask.numOfTasks() < self.max

    def searchTask(self, tid: str) -> Optional[Task]:
        return self.inProcTask.search(tid)

    def inProcTasks(self) -> List[Task]:
        return self.inProcTask.toList()

    def removeTask(self, tid: str) -> None:
        self.inProcTask.remove(tid)

    def maxNumOfTask(self) -> int:
        return self.max

    def numOfTaskProc(self) -> int:
        return self.inProcTask.numOfTasks()

    def control(self, cmd:Command) -> None:
        letter = cmd.toLetter()
        self.__send(letter)

    def do(self, task: Task) -> None:
        if not self.isAbleToAccept():
            raise Exception

        # Task assign
        letter = task.toNewTaskLetter()
        if letter is None:
            return None

        self.__send(letter)

        # Register task into task group
        task.toProcState()

        self.inProcTask.newTask(task)

    # Provide ability to cancel task in queue or
    # processed task
    # Note: sn here should be a verion sn
    def cancel(self, id: str) -> str:
        pass

    def status(self) -> Dict:
        status_dict = { "max":self.max,
                        "sock":self.sock,
                        "processing":self.inProcTask.numOfTasks(),
                        "inProcTask":self.inProcTask.toList_(),
                        "ident":self.ident}
        return status_dict

    @staticmethod
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

    @staticmethod
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