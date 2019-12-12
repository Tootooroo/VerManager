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

from manager.misc.workerRoom import WorkerRoom
from manager.misc.letter import Letter
from manager.misc.type import Ok, Error

class Task:
    STATE_PREPARE = 0
    STATE_IN_PROC = 1
    STATE_FINISHED = 2
    STATE_FAILURE = 3

    def __init__(self, id: typing.AnyStr, **content):
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
        return s >= STATE_PREPARE and s <= STATE_FAILURE

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
        self.wait_counter = 0
        self.offline_counter = 0
        self.online_counter = 0
        self.__clock = None

        # Worker is created while a connection is created between
        # worker and server. The first letter from worker to server
        # must a PropertyNotify type
        l = self.__recv()
        if Letter.typeOfLetter(l) == Letter.PropertyNotify:
            self.max = l.propNotify_MAX()
            self.processing = l.propNotify_PROC()
            self.ident = l.propNotify_IDENT()
            self.state = Worker.STATE_ONLINE
            self.__clock = datetime.utcnow()
        else:
            raise Exception

    def waitCounter(self):
        return self.wait_counter

    def offlineCounter(self):
        return self.offline_counter

    def onlineCounter(self):
        return self.online_counter

    def counterSync(self):
        delta = datetime.utcnow() - self.__clock

        if self.state == Worker.STATE_OFFLINE:
            self.offline_counter = delta.seconds
        elif self.state == Worker.STATE_ONLINE:
            self.online_counter = delta.seconds
        elif self.state == Worker.STATE_WAITING:
            self.wait_counter = delta.seconds

        return None

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

    def do(self, letter) -> None:
        if not self.isAbleToAccept():
            raise Exception

        # Task assign
        letter.addToHeader('ident', self.ident)
        self.__send(letter)

        # Register task into task group
        ident = letter.getHeader('ident')
        task = Task(ident)
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
        content = ""
        remain = Letter.MAX_LEN

        while remain > 0:
            content = sock.recv(remain)
            if content == b'':
                raise Exception
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


class EventListener(Thread):

    def __init__(self, workerRoom):
        Thread.__init__(self)
        self.entries = select.poll()
        self.workers = workerRoom
        self.numOfEntries = 0
        # Handler in handlers should be unique
        self.handlers = {}

    def registerEvent(self, eventType, handler):
        if eventType in self.handlers:
            return None

        self.handlers[eventType] = handler

    def unregisterEvent(self, eventType):
        if not eventType in self.handlers:
            return None

        del self.handlers [eventType]

    def addWorker(self, worker):
        ident = worker.getIdent()
        isNotExists = not self.workers.isExists(ident)

        if isNotExists:
            self.workers.addWorker(worker)
            # Register socket into entries
            sock = worker.sock
            self.entries.register(sock.fileno(), select.POLLIN)
            return Ok

        return Error

    def removeWorker(self, ident):
        sock = None
        isExists = self.workers.isExists(ident)

        if isExists:
            # Unregister the socket from poll object
            self.entries.unregister(sock)
            # remove worker
            self.workers.removeWorker(ident)
            return Ok

        return Error

    def getWorker(self, ident):
        return self.workers.getWorker(ident)

    def Acceptor(self, letter):
        # Check letter's type
        event = letter.type_

        if event == Letter.NewTask or event == Letter.TaskCancel:
            return None

        handler = self.handlers[event]
        handler(self, letter)

    def run(self):

        while True:
            # Polling every 10 seconds due to polling
            # may not affect to new worker which be
            # added after poll() is called
            readyEntries = self.entries.poll(10000)

            # Read message from socket and then transfer
            # this message into letter. Then hand the
            # letter to acceptor
            for fd, event in readyEntries:
                sock = socket.fromfd(fd, socket.AF_INET, socket.SOCK_STREAM)

                try:
                    letter = Worker.receving(sock)
                except:
                    self.entries.unregister(fd)
                    continue

                if letter != None:
                    self.Acceptor(letter)

# Handlers definitions

# Handler to process response of NewTask request
def responseHandler(eventListener, letter):
    # Should verify the letter's format

    ident = letter.getHeader('id')
    taskId = letter.getHeader('tId')

    state = int(letter.getContent('state'))

    worker = eventListener.getWorker(ident)
    task = worker.searchTask(taskId)

    if Task.isValidState(state):
        task.stateChange(state)

        # When Task move into STATE_FINISHED
        # should open a thread to receive generated
        # file.
        if state == Task.STATE_FINISHED:
            pass
