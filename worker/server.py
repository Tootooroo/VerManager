# server.py


import subprocess
import zipfile
import os
import socket

if __name__ == '__main__':
    import sys
    sys.path.append("../manager/misc")
    from letter import Letter
else:
    from manager.misc.letter import Letter

from multiprocessing import Pool, Queue
from threading import Thread, Condition

WORKER_NAME = "WORKER_EXAMPLE"
REPO_URL = "git@gpon.git.com:gpon/olt.git"
PROJECT_NAME = "olt"

class RESPONSE_TO_SERVER_DAEMON(Thread):

    def __init__(self, server):
        Thread.__init__(self)

        self.cond = Condition()
        self.server = server

    def run(self):
        cond = self.cond
        server = self.server

        cond.acquire()

        while True:
            cond.wait_for(self.server.isResponseInQ())
            server.transfer_step()

class TASK_DEAL_DAEMON(Thread):

    def __init__(self, server):
        Thread.__init__(self)

        self.server = server
        self.max = os.cpu_count()
        self.numOfTasksInProc = 0
        self.pool = Pool(os.cpu_count() * 2)

    def run(self):
        server = self.server

        while True:
            l = server.waitLetter()

            if not self.numOfTasksInProc < self.max:
                # Worker is unable to accept task
                # just response failure to server
                letter = Letter(Letter.Response, {"ident":"..."}, {"state":"3"})
                server.transfer(letter)

            self.numOfTasksInProc += 1
            self.pool.apply_async(self.__do, (l,))

            # STATE_IN_PROC
            letter = Letter(Letter.Response, {"ident":"..."}, {"state":"1"})
            server.transfer(letter)

    # Processing the assigned task and send back the result to server
    def __do(args):
        global REPO_URL, PROJECT_NAME

        l = args[0]
        server = args[1]

        revision = l.getContent('sn')
        vsn = l.getContent('vsn')

        # Processing
        ret = subprocess.run(["git", "clone", "-b", "master", REPO_URL])
        try:
            ret.check_returncode()
        except subprocess.CalledProcessError:
            letter = Letter(Letter.Response, {"ident":"..."}, {"state":"3"})
            server.transfer(letter)

        os.chdir(PROJECT_NAME)
        ret = subprocess.run(["git", "checkout", "-f", revision])
        ret = subprocess.run(["make"])

        # Send back to server
        with line in open("./try", 'rb'):
            binaryLetter = Letter(Letter.BinaryFile, {"tid":vsn}, {"content":line})
            server.transfer(binaryLetter)

        # Response to server to notify that the task is finished
        finishedLeter = Letter(Letter.Response, {"ident":"...", "tid":vsn}, {"state":"2"})
        server.transfer(finishedLetter)



class Server(Thread):

    def __init__(self, address):
        Thread.__init__(self)

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect(address)

        self.q = Queue(self.__numOfProcess * 256)

    def run(self):
        self.init()

    def init(self):
        global WORKER_NAME

        propLetter = Letter(Letter.PropertyNotify,\
                            {"ident":WORKER_NAME},\
                            {"MAX":str(os.cpu_count()), "PROC":"0"})
        self.__send(propLetter)

        TASK_DEAL_DAEMON(self).start()
        RESPONSE_TO_SERVER_DAEMON(self).start()

    def waitLetter(self):
        return self.__recv()

    # Transfer a letter to server
    # calling of this method will not transfer
    # a letter to server instance instead the
    # letter will first buffer into a queue
    # and RESPONSE_TO_SERVER_DAEMON will deal
    # with letters in queue
    def transfer(self, l):
        self.q.put(l)

    def transfer_step(self):
        self.__send(self.q.get())

    def isResponseInQ(self):
        return not self.q.empty()

    def __send(self, l):
        return Server.__sending(self.sock, l)

    def __recv(self):
        return Server.__receving(self.sock)

    def __receving(sock):
        content = b''
        remain = Letter.MAX_LEN

        while remain > 0:
            chunk = sock.recv(remain)
            if chun == b'':
                raise Exception

            content += chunk
            remain = Letter.letterBytesRemain(content)

        return Letter.parse(content)

    def __sending(sock, l):
        jBytes = l.toBytesWithLength()
        totalSent = 0
        length = len(jBytes)

        while totalSent < length:
            sent = sock.send(jBytes[totalSent:])
            if sent == 0:
                raise Exception
            totalSent += sent

        return None
