# MIT License
#
# Copyright (c) 2020 Gcom
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# util.py

import os
import platform
import subprocess
import socket
import asyncio

from threading import Thread
from functools import reduce
from typing import Callable, Any, Tuple, List, \
    Optional


def spawnThread(f: Callable[[Any], None], args: Any = None) -> Thread:

    class AnonyThread(Thread):
        def __init__(self):
            Thread.__init__(self)

        def run(self):
            f() if args is None else f(args)

    anony = AnonyThread()
    anony.start()

    return anony


def pathStrConcate(*args, seperator: str) -> str:
    argsL = list(args)

    argsL = list(filter(lambda s: len(s) > 0, argsL))
    argsL = list(map(lambda s: s[0:-1] if s[-1] == '/' and len(s) > 1 else s,
                     argsL))

    return reduce(lambda acc, curr:
                  acc + seperator + curr
                  if acc != '/' else acc + curr,

                  argsL)


def partition(items: List, predicate: Callable) -> Tuple[List, List]:

    trueSet = []  # type: List
    falseSet = []  # type: List

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


def packShellCommands(commands: List[str]) -> str:
    if platform.system() == 'Windows':
        return "&&".join(commands)
    else:
        return ";".join(commands)


def map_strict(f: Callable, args: List[Any]) -> List[Any]:
    return list(map(f, args))


def excepHandle(excep, handler: Callable) -> Callable:

    def handle(f: Callable) -> None:
        def handling(*args, **kwargs):
            try:
                f(*args, **kwargs)
            except excep:
                handler()

    return handle


def execute_shell(command: str) -> Optional[subprocess.Popen]:
    try:
        output_buf = open(os.devnull, "w")
        return subprocess.Popen(command, shell=True,
                                stdout=output_buf, stderr=output_buf)
    except FileNotFoundError:
        return None


async def execute_shell_until_complete(command: str) -> int:
    try:
        ref = subprocess.Popen(command, shell=True)
    except FileNotFoundError:
        return -1

    while True:
        try:
            ret_code = ref.wait(timeout=0)
        except subprocess.TimeoutExpired:
            await asyncio.sleep(1)
            continue

        return ret_code


# If shell command is not executed success then return None
# otherwise return returncode of the shell command.
def execute_shell_command(command: str) -> Optional[int]:

    proc_handle = execute_shell(command)
    if proc_handle is None:
        return None

    returncode = proc_handle.wait()

    return returncode


def isWindows() -> bool:
    return platform.system() == "Windows"


def isLinux() -> bool:
    return platform.system() == "Linux"


def sockKeepalive(sock: socket.socket, timeout: int, intvl: int) -> None:
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    if isWindows():
        args = (1, timeout*1000, intvl*1000)
        sock.ioctl(socket.SIO_KEEPALIVE_VALS, args)  # type: ignore
    else:
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, timeout)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, intvl)


async def delayExec(coro, secs=0):
    await asyncio.sleep(secs)
    await coro


async def loop_forever_async(f: Callable) -> None:
    while True:
        await f()


def loop_forever(f: Callable) -> None:
    while True:
        f()
