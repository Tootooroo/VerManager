# dispatcher.py
#
# Responsbility to version generation works dispatch,
# load-balance, queue supported

import typing
from threading import Thread

class Dispatcher(Thread):

    def __init__(self):
        Thread.__init__(self)

    def dispatch(self):
        pass
