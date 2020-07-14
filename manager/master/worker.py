# worker.py
#
# Maintain connection with workers and
# provide communication interface to another module

import socket
import traceback
import asyncio

from typing import Tuple, Optional, List, Dict, Callable
from .task import Task, TaskGroup, SingleTask, PostTask
from datetime import datetime
from threading import Lock
from manager.basic.letter import Letter, receving as letter_receving, \
    sending as letter_sending, CancelLetter
from manager.basic.commands import Command


WorkerState = int


class WorkerInitFailed(Exception):
    pass


class Worker:

    STATE_ONLINE = 0
    STATE_WAITING = 1
    STATE_OFFLINE = 2

    def __init__(self, reader: asyncio.StreamReader,
                 writer: asyncio.StreamWriter) -> None:

        self.role = None  # type: Optional[int]

        self._reader = reader
        self._writer = writer
        self.address = "0.0.0.0"

        self.max = 0
        self.inProcTask = TaskGroup()
        self.menus = []  # type: List[Tuple[str, str]]
        self.ident = ""
        self.needUpdate = False

        # Before a PropertyNotify letter is report
        # from worker we see a worker as an offline
        # worker
        self.state = Worker.STATE_OFFLINE

        # Counters
        # 1.wait_counter: ther number of seconds
        #                 that a worker stay in STATE_WAITING
        # 2.offline_counter: the number of seconds that a worker
        #                    stay in STATE_OFFLINE
        # 3.online_counter: the number of seconds that a worker stay
        #                   in STATE_ONLINE
        # 4.clock: Record the time while state of Worker is changed
        #          and counter 1 to 3 is calculated via
        #          clock. Clock is not accessable by user directly.
        #
        # counters[STATE_ONLINE] : online_counter
        # counters[STATE_WAITING] : wait_counter
        # counters[STATE_OFFLINE] : offline_counter
        self.counters = [0, 0, 0]
        self._clock = datetime.now()

    async def active(self) -> None:
        letter = await self._recv()

        if letter is None:
            raise WorkerInitFailed()

        if Letter.typeOfLetter(letter) == Letter.PropertyNotify:
            self.max = letter.propNotify_MAX()
            self.ident = letter.propNotify_IDENT()
            self.address = "0.0.0.0"
            self.state = Worker.STATE_ONLINE
            self._clock = datetime.utcnow()
        else:
            raise WorkerInitFailed()

    def getStream(self) -> Tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        return (self._reader, self._writer)

    def setStream(self, stream: Tuple[asyncio.StreamReader, asyncio.StreamWriter]) -> None:
        self._reader, self._writer = stream

    def waitCounter(self) -> int:
        self._counterSync()
        return self.counters[Worker.STATE_WAITING]

    def offlineCounter(self) -> int:
        self._counterSync()
        return self.counters[Worker.STATE_OFFLINE]

    def onlineCounter(self) -> int:
        self._counterSync()
        return self.counters[Worker.STATE_ONLINE]

    def _counterSync(self) -> None:
        delta = datetime.utcnow() - self._clock
        self.counters[self.state] = delta.seconds

    def setState(self, s: WorkerState) -> None:
        if self.state != s:
            self.counters[self.state] = 0

        self.state = s
        self._clock = datetime.utcnow()

    def getAddress(self) -> str:
        return self.address

    def setAddress(self, address: str) -> None:
        self.address = address

    def getIdent(self) -> str:
        return self.ident

    def isOnline(self) -> bool:
        return self.state == Worker.STATE_ONLINE

    def isWaiting(self) -> bool:
        return self.state == Worker.STATE_WAITING

    def isOffline(self) -> bool:
        return self.state == Worker.STATE_OFFLINE

    def isFree(self) -> bool:
        return self.inProcTask.numOfTasks() == 0

    def isAbleToAccept(self) -> bool:
        return self.inProcTask.numOfTasks() < self.max

    def searchTask(self, tid: str) -> Optional[Task]:
        return self.inProcTask.search(tid)

    def inProcTasks(self) -> List[Task]:
        return self.inProcTask.toList()

    def removeTask(self, tid: str) -> None:
        self.inProcTask.remove(tid)

    def removeTaskWithCond(self, predicate: Callable[[Task], bool]) -> None:
        return self.inProcTask.removeTasks(predicate)

    def maxNumOfTask(self) -> int:
        return self.max

    def numOfTaskProc(self) -> int:
        return self.inProcTask.numOfTasks()

    async def control(self, cmd: Command) -> None:
        letter = cmd.toLetter()
        await self._send(letter)

    async def do(self, task: Task) -> None:
        letter = task.toLetter()

        if letter is None:
            raise Exception

        await self._send(letter)

        # Register task into task group
        task.toProcState()

        self.inProcTask.newTask(task)

    # Provide ability to cancel task in queue or
    # processed task
    # Note: sn here should be a verion sn
    def cancel(self, id: str) -> None:

        task = self.inProcTask.search(id)
        if task is None:
            return None

        letter = CancelLetter(id, CancelLetter.TYPE_SINGLE)

        if isinstance(task, SingleTask):
            self._send(letter)

        elif isinstance(task, PostTask):
            letter.setType(CancelLetter.TYPE_POST)
            self._send(letter)

        self.inProcTask.remove(id)

    def status(self) -> Dict:
        status_dict = {
            "max": self.max,
            "processing": self.inProcTask.numOfTasks(),
            "inProcTask": self.inProcTask.toList_(),
            "ident": self.ident
        }
        return status_dict

    @staticmethod
    async def receving(reader: asyncio.StreamReader, timeout=None) -> Optional[Letter]:
        return await letter_receving(reader, timeout=timeout)

    @staticmethod
    async def sending(writer: asyncio.StreamWriter, l: Letter) -> None:
        return await letter_sending(writer, l)

    async def _recv(self, timeout=None) -> Optional[Letter]:
        return await Worker.receving(self._reader, timeout=timeout)

    async def _send(self, l: Letter) -> None:
        try:
            await Worker.sending(self._writer, l)
        except Exception:
            traceback.print_exc()



# TestCases
import unittest

class WorkerTestCases(unittest.TestCase):

    def test_worker(self):
        import time
        from manager.basic.util import spawnThread
        from manager.master.build import Build, Merge
        from manager.master.task import SingleTask, PostTask
        from manager.basic.letter import sending as l_send, receving as l_recv, \
            NewLetter, PostTaskLetter, PropLetter
        from socket import socket, AF_INET, SOCK_STREAM
        from manager.master.worker import Worker

        Max = "2"
        InProc = "0"

        canceled = False

        async def worker_connect(server_task):
            # Wait Server start
            await asyncio.sleep(1)

            reader, writer = await asyncio.open_connection(
                "127.0.0.1", 9999
            )

            # Send PropLetter
            prop_l = PropLetter("TestWorker", Max, InProc)
            await l_send(writer, prop_l)

            l = await l_recv(reader)
            if l is None:
                self.assertTrue(False)
            else:
                if isinstance(l, NewLetter):
                    pass
                else:
                    self.assertTrue(False)

            l = await l_recv(reader)
            if l is None:
                self.assertTrue(False)
            else:
                if isinstance(l, PostTaskLetter):
                    pass
                else:
                    self.assertTrue(False)

            while canceled is False:
                await asyncio.sleep(1)

            if canceled is True:
                server_task.cancel()

        async def server_mock():
            server = await asyncio.start_server(
                handler, '127.0.0.1', 9999
            )

            await server.serve_forever()

        async def handler(r: asyncio.StreamReader,
                          w: asyncio.StreamWriter):

            worker = Worker(r, w)
            await worker.active()

            # Prop Assert
            self.assertEqual(int(Max), worker.maxNumOfTask())
            self.assertEqual(int(InProc), len(worker.inProcTasks()))

            # Send a task to worker
            build = Build("B_TEST", {'cmd':["cmd1", "cmd2"], 'output':["./output"]})
            await worker.do(SingleTask("Test", "SN", "REV", build, {}))

            # Now inProc task should be 1
            inProcTasks = worker.inProcTasks()
            self.assertTrue(1, len(inProcTasks))

            task = inProcTasks[0]
            self.assertEqual("Test", task.id())
            self.assertEqual("SN", task.getSN())
            self.assertEqual("REV", task.getVSN())

            # Now Send a PostTask
            build_post = Build("B_TEST", {'cmd':["cmd1", "cmd2"], 'output':["./output"]})
            await worker.do(PostTask("PostTest", "VSN", [], [], Merge(build_post)))

            inProcTasks = worker.inProcTasks()
            self.assertTrue(2, len(inProcTasks))

            self.assertTrue("Test" in [t.id() for t in inProcTasks])
            self.assertTrue("PostTest" in [t.id() for t in inProcTasks])

            # Remove tasks
            worker.removeTask("Test")
            inProcTasks = worker.inProcTasks()
            self.assertEqual(1, len(inProcTasks))
            self.assertTrue("Test" not in [t.id() for t in inProcTasks])
            self.assertTrue("PostTest" in [t.id() for t in inProcTasks])

            worker.removeTask("PostTest")
            inProcTasks = worker.inProcTasks()
            self.assertEqual(0, len(inProcTasks))
            self.assertTrue("Test" not in [t.id() for t in inProcTasks])
            self.assertTrue("PostTest" not in [t.id() for t in inProcTasks])

            nonlocal canceled
            canceled = True

        async def test_main() -> None:
            server_task = asyncio.create_task(server_mock())

            await asyncio.gather(
                server_task,
                worker_connect(server_task)
            )

        try:
            asyncio.run(test_main())
        except asyncio.exceptions.CancelledError:
            pass
