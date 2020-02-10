# util.py

from typing import Any, Callable
from threading import Thread

from functools import reduce

from typing import *

def spawnThread(f:Callable[[Any], None], args: Any = None) -> Thread:

    class AnonyThread(Thread):
        def __init__(self):
            Thread.__init__(self)

        def run(self):
            f() if args == None else f(args)

    anony = AnonyThread()
    anony.start()

    return anony

def pathStrConcate(*args, seperator:str) -> str:
    argsL = list(args)

    argsL = list(filter(lambda s: len(s) > 0, argsL))
    argsL = list(map(lambda s: s[0:-1] if s[-1] == '/' and len(s) > 1 else s, argsL))

    return reduce(lambda acc, curr: acc + seperator + curr if acc != '/' else acc + curr, argsL)
