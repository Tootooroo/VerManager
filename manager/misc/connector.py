# connector.py
#
# Maintain connection with workers and
# provide communication interface to another module

import socket

from multiprocessing import Process
from threading import Thread

MAX_NUM_OF_USERS = 10

class Connector(Thread):

    def __init__(self):
        self.masterSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.masterSock.bind(("Host", "Port"))
        self.masterSock.listen(MAX_NUM_OF_USERS)

    def run(self):
        pass
