# worker.py
#
# Maintain connection with workers and
# provide communication interface to another module

import socket
import typing
import select

from functools import reduce
from threading import Thread, Lock

from manager.misc.letter import Letter
from manager.misc.type import *

class Task:
    STATE_PREPARE = 0
    STATE_IN_PROC = 1
    STATE_FINISHED = 2
    STATE_FAILURE = 3

    def __init__(self, id):
        self.taskId = id
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
        pass

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
        del self.__dict_tasks [id]

    def finidhed(self, id):
        task = self.__dict_tasks[id]
        task.stateChange(Task.STATE_FINISHED)

        return Ok

    def failure(self, id):
        task = self.__dict_tasks[id]
        task.stateChange(Task.STATE_FAILURE)

        return Ok

    def search(self, id):
        return self.__dict_tasks[id]

class Worker(socket.socket):

    def __init__(self, sock):
        self.sock = sock
        self.max = 0
        self.processing = 0
        self.inProcTask = TaskGroup()
        self.ident = None
        self.lock = Lock()

        # Worker is created while a connection is created between
        # worker and server. The first letter from worker to server
        # must a PropertyNotify type
        l = self.__recv()
        if Letter.typeOfLetter(l) == Letter.PropertyNotify:
            self.max = l.propNotify_MAX()
            self.processing = l.propNotify_PROC()
            self.ident = l.propNotify_IDENT()
        else:
            raise Exception

    def getIdent(self):
        return self.ident

    def isFree(self) -> bool:
        return self.processing == 0

    def isAbleToAccept(self) -> bool:
        return self.processing < self.max

    def searchTask(self, tid):
        pss

    def do(self, header: typing.Dict, content: typing.Dict) -> None:
        if not self.isAbleToAccept():
            raise Exception

        # Task assign
        header['ident'] = self.ident
        do_letter = Letter(Letter.NewTask, header, content)
        self.__send(do_letter)

        # Register task into task group
        ident = do_letter.getHeader('ident')
        task = Task(ident)
        task.stateChange(Task.STATE_IN_PROC)

        with self.lock:
            self.inProcTask.newTask(task)

    # Provide ability to cancel task in queue or
    # processed task
    # Note: sn here should be a version sn
    def cancel(self, id: typing.AnyStr):
        pass

    def receving(sock):
        content = None
        received = 0
        MAX_LEN = Letter.MAX_LEN

        content = sock.recv(Letter.MAX_LEN)
        print(content)
        if content == b'':
            return None

        content_decoded = content.decode()
        end = content_decoded.find('{')
        MAX_LEN = int(content_decoded[:end])

        # length of length field should be substract
        received = len(content) - end

        while received < MAX_LEN:
            chunk = sock.recv(MAX_LEN - received)
            if chunk == b'':
                return None
            received += len(chunk)
            content += chunk

        return Letter.json2Letter(content.decode())

    def sending(sock, l):
        jBytes = l.toString().encode()
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

    def __init__(self):
        Thread.__init__(self)
        self.entries = select.poll()
        # Worker in workers should be unique
        self.workers = []
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
        isNotExists = list(filter(lambda w: w.ident() == ident, self.workers)) == []

        if isNotExists:
            self.workers.append(worker)
            # Register socket into entries
            sock = worker.sock
            self.entries.register(sock, select.POLLIN)
            return Ok

        return Error

    def removeWorker(self, ident):
        sock = None

        def f(w):
            w.ident() == ident
            sock = w.sock

        isExists = list(filter(f, self.workers)) != []

        if isExists:
            # Unregister the socket from poll object
            self.entries.unregister(sock)
            # remove worker
            self.workers.remove(index)
            return Ok

        return Error

    def getWorker(self, ident):
        pass

    def Acceptor(self, letter):
        # Check letter's type
        event = letter.type_

        if event == Letter.NewTask or event == Letter.TaskCancel:
            return None

        handler = self.handlers[event]
        handler(self, letter)

    def run(self):

        while True:
            readyEntries = self.entries.poll()

            # Read message from socket and then transfer
            # this message into letter. Then hand the
            # letter to acceptor
            for fd, event in readyEntries:
                sock = socket.fromfd(fd, socket.AF_INET, socket.SOCK_STREAM)
                letter = Worker.receving(sock)

                if letter != None:
                    self.Acceptor(letter)

# Handlers definitions

# Handler to process response of NewTask request
def responseHandler(eventListener, letter):
    ident = letter.getHeader('id')
    taskId = letter.getHeader('tId')

    state = letter.getContent('state')

    worker = eventListener.getWorker(ident)
    task = worker.searchTask(taskId)

    if Task.isValidState(state):
        task.stateChange(state)

        # In finished state data field of Task should be
        # set correctly.
        if state == Task.STATE_FINISHED:
            pass
