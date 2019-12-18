# worker.py
#
# Maintain connection with workers and
# provide communication interface to another module

import socket
import typing
import select
from datetime import datetime, timedelta

from functools import reduce
from threading import Thread, Lock

from manager.misc.letter import Letter
from manager.misc.type import Ok, Error

class Task:
    STATE_PREPARE = 0
    STATE_IN_PROC = 1
    STATE_FINISHED = 2
    STATE_FAILURE = 3

    def __init__(self, id: typing.AnyStr, content):
        self.taskId = id

        self.content = content
        self.state = Task.STATE_PREPARE

        # This field will be set by EventListener while
        # the task is complete by worker and transfer
        # totally
        self.data = None

    def id(self):
        return self.taskId

    def taskState(self):
        return self.state

    def stateChange(self, state):
        self.state = state

    def setData(self, data):
        self.data = data

    def isProc(self):
        return self.state == Task.STATE_IN_PROC

    def isFailure(self):
        return self.state == Task.STATE_FAILURE

    def isFinished(self):
        return self.state == Task.STATE_FINISHED

    def isValidState(s):
        return s >= Task.STATE_PREPARE and s <= Task.STATE_FAILURE

class TaskGroup:
    def __init__(self):
        self.__dict_tasks = {}
        self.__numOfTasks = 0

    def newTask(self, task):
        self.__dict_tasks[task.id()] = task
        self.__numOfTasks += 1

    def remove(self, id):
        if id in self.__dict_tasks:
            del self.__dict_tasks [id]
            return Ok
        return Error

    def finidhed(self, id):
        task = self.search(id)
        task.stateChange(Task.STATE_FINISHED)

        return Ok

    def failure(self, id):
        task = self.search(id)
        task.stateChange(Task.STATE_FAILURE)

        return Ok

    def search(self, id):
        if not id in self.__dict_tasks:
            return None

        return self.__dict_tasks[id]

class Worker(socket.socket):

    STATE_ONLINE = 0
    STATE_WAITING = 1
    STATE_OFFLINE = 2

    def __init__(self, sock):
        self.sock = sock
        self.max = 0
        self.processing = 0
        self.inProcTask = TaskGroup()
        self.ident = None

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
        self.__clock = None

        # Prevent permanent blocking from waiting for PropertyNotify from worker
        self.sock.settimeout(10)

        # Worker is created while a connection is created between
        # worker and server. The first letter from worker to server
        # must a PropertyNotify type
        l = self.__recv()

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

    def waitCounter(self):
        return self.counters[Worker.STATE_WAITING]

    def offlineCounter(self):
        return self.counters[Worker.STATE_OFFLINE]

    def onlineCounter(self):
        return self.counters[Worker.STATE_ONLINE]

    def counterSync(self):
        delta = datetime.utcnow() - self.__clock
        self.counters[self.state] = delta.seconds

    def getState(self):
        return self.state

    def setState(self, s):
        self.state = s
        return None

    def getIdent(self):
        return self.ident

    def isOnline(self):
        return self.state == Worker.STATE_ONLINE

    def isWaiting(self):
        return self.state == Worker.STATE_WAITING

    def isOffline(self):
        return self.state == Worker.STATE_OFFLINE

    def isFree(self) -> bool:
        return self.processing == 0

    def isAbleToAccept(self) -> bool:
        return self.processing < self.max

    def searchTask(self, tid: typing.AnyStr):
        with self.lock:
            return self.inProcTask.search(tid)

    def removeTask(self, tid: typing.AnyStr):
        with self.lock:
            self.processing -= 1
            return self.inProcTask.remove(tid)

    def numOfTaskProc(self):
        return self.processing

    def do(self, task) -> None:
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
    def cancel(self, id: typing.AnyStr):
        pass

    # fixme: should support binary letter
    def receving(sock):
        content = b''
        remain = Letter.MAX_LEN

        while remain > 0:
            chunk = sock.recv(remain)
            if chunk == b'':
                raise Exception

            content += chunk
            remain = Letter.letterBytesRemain(content)

        return Letter.parse(content)

    def sending(sock, l):
        jBytes = l.toBytesWithLength()
        totalSent = 0
        length = len(jBytes)

        while totalSent < length:
            sent = sock.send(jBytes[totalSent:])
            if sent == 0:
                raise Exception
            totalSent += sent

    def __recv(self):
        return Worker.receving(self.sock)

    def __send(self, l):
        return Worker.sending(self.sock, l)
