# util.py

import platform

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

def partition(items:List, predicate:Callable) -> Tuple[List, List]:

    trueSet = [] # type: List
    falseSet = [] # type: List

    for item in items:

        if predicate(item):
            trueSet.append(item)
        else:
            falseSet.append(item)

    return (trueSet, falseSet)

def pathSeperator() -> str:
    if platform.system() == 'Windows':
        return "\\"
    else:
        return "/"

def map_strict(f:Callable, args:List[Any]) -> List[Any]:
    return list(map(f, args))

def excepHandle(excep, handler:Callable) -> Callable:

    def handle(f:Callable) -> None:
        def handling(*args, **kwargs):
            try:
                f(*args, **kwargs)
            except excep:
                handler()

    return handle
