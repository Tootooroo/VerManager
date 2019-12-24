# server.py
# Usage: python server.py <configPath>

import sys
import subprocess
import zipfile
import os
import socket
import time

from threading import Lock

if __name__ == '__main__':
    import sys
    sys.path.append("../manager/misc")

    from letter import Letter
    from info import Info
    from type import *
else:
    from manager.misc.letter import Letter
    from worker.info import Info
    from manager.misc.type import *

from multiprocessing import Pool, Queue, Manager
from threading import Thread, Condition

class RESPONSE_TO_SERVER_DAEMON(Thread):

    def __init__(self, server, info):
        Thread.__init__(self)

        self.cond = Condition()
        self.server = server

    def run(self):
        cond = self.cond
        server = self.server

        cond.acquire()

        while True:
            ret = server.transfer_step()

            while ret == Error:
                # Waiting for <TASK_DEAL_DAEMON> reconnecting
                time.sleep(5)
                continue

class TASK_DEAL_DAEMON(Thread):

    def __init__(self, server, info):
        Thread.__init__(self)

        self.server = server
        self.max = info.getConfig('MAX_TASK_CAN_PROC')
        self.numOfTasksInProc = 0
        self.pool = Pool(info.getConfig('PROCESS_POOL_SIZE'))
        self.info = info

    def run(self):
        WORKER_NAME = self.info.getConfig('WORKER_NAME')
        server = self.server

        while True:
            l = server.waitLetter()

            if l == None:
                server.reconnectUntil(5)
                continue

            print("Received letter:" + l.toString())

            if not self.numOfTasksInProc < self.max:
                # Worker is unable to accept task
                # just response failure to server
                letter = Letter(Letter.Response, {"ident":WORKER_NAME}, {"state":"3"})
                server.transfer(letter)
                continue

            self.numOfTasksInProc += 1
            res = self.pool.apply_async(TASK_DEAL_DAEMON.job, (server, l, self.info))
            res.get()

    # Processing the assigned task and send back the result to server
    def job(*args):
        server = args[0]
        letter = args[1]
        info = args[2]

        REPO_URL = info.getConfig('REPO_URL')
        PROJECT_NAME = info.getConfig('PROJECT_NAME')
        WORKER_NAME = info.getConfig('WORKER_NAME')
        BUILDING_CMDS = info.getConfig('BUILDING_CMDS')
        RESULT_PATH = info.getConfig('RESULT_PATH')

        print(REPO_URL)

        # Notify to server the worker is in processing
        letterInProc = Letter(Letter.Response, \
                        {"ident":WORKER_NAME, "tid":letter.getContent('vsn')},\
                        {"state":"1"})
        server.transfer(letterInProc)

        revision = letter.getContent('sn')
        vsn = letter.getContent('vsn')

        # Processing
        try:
            # Fetch
            ret = subprocess.run(["git", "clone", "-b", "master", REPO_URL])
            ret.check_returncode()

            os.chdir(PROJECT_NAME)

            # Revision checkout
            ret = subprocess.run(["git", "checkout", "-f", revision])
            ret.check_returncode()

            # Building
            for cmd in BUILDING_CMDS:
                ret = subprocess.run([cmd])
                ret.check_returncode()

            # Send back to server
            with open(RESULT_PATH, 'rb') as file:
                for line in file:
                    binaryLetter= Letter(Letter.BinaryFile, {"tid":vsn}, {"bytes":line})
                    server.transfer(binaryLetter)
                    time.sleep(0.05)

            # Response to server to notify that the task is finished
            finishedLetter = Letter(Letter.Response, {"ident":WORKER_NAME, "tid":vsn}, {"state":"2"})
            server.transfer(finishedLetter)

            os.chdir("..")
            ret = subprocess.run(["rm", "-rf", PROJECT_NAME])

        except subprocess.CalledProcessError:
            letter = Letter(Letter.Response, {"ident":WORKER_NAME, "tid":vsn},\
                            {"state":"3"})
            server.transfer(letter)
            return None


class Server:

    STATE_CONNECTED = 0
    STATE_CONNECTING = 1
    STATE_DISCONNECTED = 2

    def __init__(self, info):
        self.info = info

        queueSize = info.getConfig('QUEUE_SIZE')
        self.q = Manager().Queue(queueSize)

    def init(self):
        return self.connect()


    def connect(self):
        host = self.info.getConfig('MASTER_ADDRESS', 'host')
        port = self.info.getConfig('MASTER_ADDRESS', 'port')

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))

        WORKER_NAME = self.info.getConfig('WORKER_NAME')
        MAX_TASK_CAN_PROC = self.info.getConfig('MAX_TASK_CAN_PROC')


        propLetter = Letter(Letter.PropertyNotify,\
                            {"ident":WORKER_NAME},\
                            {"MAX":str(MAX_TASK_CAN_PROC), "PROC":"0"})
        if self.__send(propLetter) == Error:
            return Error

        return Ok


    def disconnect(self):
        self.sock.shutdown(socket.SHUT_RDWR)

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
        response = self.q.get()
        return self.__send(response)

    def reconnectUntil(self, timeout = None):
        ret = Error

        while ret == Error:
            print("reconnect")
            ret = self.reconnect()
            time.sleep(timeout)

        return ret


    def reconnect(self):
        return self.connect()

    def isResponseInQ(self):
        return not self.q.empty()

    def __send(self, l):
        try:
            if l.typeOfLetter() == Letter.BinaryFile:
                Server.__sending_bytes(self.sock, l.binaryPack())
            else:
                Server.__sending(self.sock, l)
            return Ok
        except:
            return Error

    def __send_bytes(self, b):
        try:
            Server.__sending_bytes(self.sock, b)
            return Ok
        except:
            return Error

    def __recv(self):
        try:
            return Server.__receving(self.sock)
        except:
            return None

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
        return Server.__sending_bytes(sock, jBytes)

    def __sending_bytes(sock, bytesBuffer):
        totalSent = 0
        length = len(bytesBuffer)

        while totalSent < length:
            sent = sock.send(bytesBuffer[totalSent:])
            if sent == 0:
                raise Exception
            totalSent += sent

        return None

if __name__ == '__main__':
    configPath = sys.argv[1]

    info = Info(configPath)

    s = Server(info)
    s.init()

    t1 = TASK_DEAL_DAEMON(s, info)
    t2 = RESPONSE_TO_SERVER_DAEMON(s, info)

    t1.start()
    t2.start()

    t1.join()
    t2.join()
