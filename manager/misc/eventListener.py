import socket
import select
from threading import Thread

from manager.misc.worker import Worker
from manager.misc.type import *
from manager.misc.workerRoom import WorkerRoom
from manager.misc.letter import Letter

class EventListener(Thread):

    def __init__(self, workerRoom):
        Thread.__init__(self)
        self.entries = select.poll()
        self.workers = workerRoom
        self.numOfEntries = 0
        # Handler in handlers should be unique
        self.handlers = {}

        # {tid:fd}
        self.taskResultFdSet = {}

    def registerEvent(self, eventType, handler):
        if eventType in self.handlers:
            return None

        self.handlers[eventType] = handler

    def unregisterEvent(self, eventType):
        if not eventType in self.handlers:
            return None

        del self.handlers [eventType]

    def fdRegister(self, worker):
        sock = worker.sock
        self.entries.register(sock.fileno(), select.POLLIN)

    def fdUnregister(self, ident):
        worker = self.getWorker(ident)
        sock = worker.sock

        self.entries.unregister(sock.fileno())

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
            readyEntries = self.entries.poll(1000)

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

        # Do some operation after finished such as close file description
        # of received binary
        if state == Task.STATE_FINISHED:
            pass

def binaryHandler(eventListener, letter):
    fdSet = eventListener.taskResultFdSet
    tid = letter.getHeader('tid')

    # This is the first binary letter of the task correspond to the
    # received tid just open a file and store the relation into fdSet
    if not tid in fdSet:
        pass

    fd = fdSet[tid]
    content = letter.getContent('content')
    fd.write(content)
