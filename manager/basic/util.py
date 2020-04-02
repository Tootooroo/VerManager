# util.py

import platform
import subprocess
import socket

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

def packShellCommands(commands:List[str]) -> str:
    if platform.system() == 'Windows':
        return "&&".join(commands)
    else:
        return ";".join(commands)

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

def execute_shell(command:str) -> Optional[subprocess.Popen]:
    try:
        return subprocess.Popen(command, shell=True)
    except FileNotFoundError:
        return None

# If shell command is not executed success then return None
# otherwise return returncode of the shell command.
def execute_shell_command(command:str) -> Optional[int]:

    proc_handle = execute_shell(command)
    if proc_handle is None:
        return None

    returncode = proc_handle.wait()

    return returncode

def isWindows() -> bool:
    return platform.system() == "Windows"

def isLinux() -> bool:
    return platform.system() == "Linux"

def sockKeepalive(sock:socket.socket, timeout:int, intvl:int) -> None:
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    if isWindows():
        sock.ioctl(socket.SIO_KEEPALIVE_VALS, (1, timeout*1000, intvl*1000)) # type: ignore
    else:
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, timeout)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, intvl)
