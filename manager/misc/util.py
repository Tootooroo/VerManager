# util.py

from typing import Any, Callable
from threading import Thread

from typing import *

def spawnThread(f:Callable[[Any], None], args: Any) -> Thread:

    class AnonyThread(Thread):
        def __init__(self):
            Thread.__init__(self)

        def run(self):
            f(args)

    anony = AnonyThread()
    return anony
