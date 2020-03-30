# worker.py
#
# Maintain connection with workers and
# provide communication interface to another module

import socket
import select
import traceback

from typing import Tuple, Optional, List, Dict, Callable

from .task import Task, TaskGroup, SingleTask, PostTask
from datetime import datetime, timedelta

from functools import reduce
from threading import Thread, Lock

from manager.basic.letter import Letter, NewLetter, \
    receving as letter_receving, sending as letter_sending, CancelLetter
from manager.basic.type import Ok, Error
from manager.basic.commands import Command
from threading import Lock

from manager.master.build import Post

class WorkerInitFailed(Exception): pass

WorkerState = int

class Worker:

    STATE_ONLINE = 0
    STATE_WAITING = 1
    STATE_OFFLINE = 2

    def __init__(self, sock: socket.socket, address:Tuple[str, int]) -> None:
        self.role = None # type: Optional[int]
        self.sock = sock
        self.address = address
        self.max = 0
        self.inProcTask = TaskGroup()
        self.menus = [] # type: List[Tuple[str, str]]
        self.ident = ""

        self.sendLock = Lock()

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

    def removeTaskWithCond(self, predicate:Callable[[Task], bool]) -> None:
        return self.inProcTask.removeTasks(predicate)

    def maxNumOfTask(self) -> int:
        return self.max

    def numOfTaskProc(self) -> int:
        return self.inProcTask.numOfTasks()

    def control(self, cmd:Command) -> None:
        letter = cmd.toLetter()
        self.__send(letter)

    def do(self, task: Task) -> None:
        letter = task.toLetter()

        if letter is None:
            raise Exception

        self.__send(letter)

        # Register task into task group
        task.toProcState()

        self.inProcTask.newTask(task)

    # Provide ability to cancel task in queue or
    # processed task
    # Note: sn here should be a verion sn
    def cancel(self, id: str) -> None:

        task = self.inProcTask.search(id)
        if task is None:
            return None

        letter = CancelLetter(id, CancelLetter.TYPE_SINGLE)

        if isinstance(task, SingleTask):
            self.__send(letter)

        elif isinstance(task, PostTask):
            letter.setType(CancelLetter.TYPE_POST)
            self.__send(letter)

        self.inProcTask.remove(id)


    def status(self) -> Dict:
        status_dict = { "max":self.max,
                        "sock":self.sock,
                        "processing":self.inProcTask.numOfTasks(),
                        "inProcTask":self.inProcTask.toList_(),
                        "ident":self.ident}
        return status_dict

    @staticmethod
    def receving(sock: socket.socket) -> Optional[Letter]:
        return letter_receving(sock)

    @staticmethod
    def sending(sock: socket.socket, l: Letter) -> None:
        return letter_sending(sock, l)

    def __recv(self) -> Optional[Letter]:
        return Worker.receving(self.sock)

    def __send(self, l: Letter) -> None:
        try:
            with self.sendLock: Worker.sending(self.sock, l)
        except:
            traceback.print_exc()
