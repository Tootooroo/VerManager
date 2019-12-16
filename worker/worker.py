# worker.py

import sys
sys.path.append("../manager/misc")

import subprocess
import zipfile
import os
import socket

from letter import Letter

from multiprocessing import Pool
from threading import Thread

class Worker(Thread):

    def __init__(self):
        Thread.__init__(self)
        self.__host = 'localhost'
        self.__port = 8012
        self.__pool = Pool()
        self.__numOfProcess = os.cpu_count()

    def run(self):
        serverSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        serverSock.connect((self.__host, self.__port))

        propLetter = Letter(Letter.PropertyNotify,\
                            {"ident":"worker_example"},\
                            {"MAX":str(self.__numOfProcess), "PROC":"0"})
