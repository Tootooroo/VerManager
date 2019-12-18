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

from multiprocessing import Pool, Queue, Manager
from threading import Thread, Condition

WORKER_NAME = "WORKER_EXAMPLE"
REPO_URL = "git@gpon.git.com:root/daemon.git"
PROJECT_NAME = "daemon"

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
            server.transfer_step()

class TASK_DEAL_DAEMON(Thread):

    def __init__(self, server):
        Thread.__init__(self)

        self.server = server
        self.max = os.cpu_count()
        self.numOfTasksInProc = 0
        self.pool = Pool(os.cpu_count() * 2)

    def run(self):
        global WORKER_NAME
        server = self.server

        while True:
            l = server.waitLetter()
            print("Received letter:" + l.toString())

            if not self.numOfTasksInProc < self.max:
                # Worker is unable to accept task
                # just response failure to server
                letter = Letter(Letter.Response, {"ident":WORKER_NAME}, {"state":"3"})
                server.transfer(letter)
                continue

            self.numOfTasksInProc += 1
            res = self.pool.apply_async(TASK_DEAL_DAEMON.job, (server, l))

            # STATE_IN_PROC
            letter = Letter(Letter.Response, \
                            {"ident":WORKER_NAME, "tid":l.getContent('vsn')},\
                            {"state":"1"})

            server.transfer(letter)

            res.get()

    # Processing the assigned task and send back the result to server
    def job(*args):
        global REPO_URL, PROJECT_NAME, WORKER_NAME

        server = args[0]
        letter = args[1]

        revision = letter.getContent('sn')
        vsn = letter.getContent('vsn')

        # Processing
        ret = subprocess.run(["git", "clone", "-b", "master", REPO_URL])
        try:
            ret.check_returncode()
        except subprocess.CalledProcessError:
            letter = Letter(Letter.Response, {"ident":WORKER_NAME, "tid":vsn},\
                            {"state":"3"})
            server.transfer(letter)
            return None

        os.chdir(PROJECT_NAME)
        ret = subprocess.run(["git", "checkout", "-f", revision])
        ret = subprocess.run(["make"])

        # Send back to server
        with open("./try", 'rb') as file:
            for line in file:
                binaryLetter= Letter(Letter.BinaryFile, {"tid":vsn}, {"bytes":line})
                server.transfer(binaryLetter)

        # Response to server to notify that the task is finished
        finishedLetter = Letter(Letter.Response, {"ident":WORKER_NAME, "tid":vsn}, {"state":"2"})
        server.transfer(finishedLetter)



class Server:

    def __init__(self, host, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))

        self.q = Manager().Queue(os.cpu_count() * 256)

    def init(self):
        global WORKER_NAME

        propLetter = Letter(Letter.PropertyNotify,\
                            {"ident":WORKER_NAME},\
                            {"MAX":str(os.cpu_count()), "PROC":"0"})
        self.__send(propLetter)

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
        if l.typeOfLetter() == Letter.BinaryFile:
            return Server.__sending_bytes(self.sock, l.binaryPack())
        else:
            return Server.__sending(self.sock, l)

    def __send_bytes(self, b):
        return Server.__sending_bytes(self.sock, b)

    def __recv(self):
        return Server.__receving(self.sock)

    def __receving(sock):
        content = b''
        remain = Letter.MAX_LEN

        while remain > 0:
            chunk = sock.recv(remain)
            if chunk == b'':
                raise Exception

            content += chunk
            remain = Letter.letterBytesRemain(content)

        return Letter.parse(content)

    def __sending(sock, l):
        jBytes = l.toBytesWithLength()
        Server.__sending_bytes(sock, jBytes)

    def __sending_bytes(sock, bytesBuffer):
        totalSent = 0
        length = len(bytesBuffer)

        while totalSent < length:
            sent = sock.send(bytesBuffer[totalSent:])
            if sent == 0:
                raise Exception
            totalSent += sent

        return None
