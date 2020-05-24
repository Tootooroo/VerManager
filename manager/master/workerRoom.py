# connector.py
#
# Maintain connection with workers

from django.test import TestCase # type: ignore

import time
import socket

from datetime import datetime

from threading import Lock, Condition

from manager.basic.observer import Subject, Observer
from manager.basic.type import State, Error, Ok
from manager.master.worker import Worker, WorkerInitFailed

from manager.basic.mmanager import ModuleDaemon

from queue import Queue, Empty, Full

from manager.basic.util import spawnThread

from manager.basic.commands import Command, LisAddrUpdateCmd
from manager.master.task import Task

from manager.master.postElectProtos import RandomElectProtocol
from manager.master.postElection import PostManager

from manager.basic.letter import CmdResponseLetter

from typing import Tuple, Callable, Any, List, Dict, Optional

from manager.basic.info import M_NAME as INFO_M_NAME

from manager.basic.commands import AcceptCommand, AcceptRstCommand, \
    LisLostCommand

M_NAME = "WorkerRoom"

# Type alias
EVENT_TYPE = int
hookTuple = Tuple[Callable[[Worker, Any], None], Any]
filterFunc = Callable[[List[Worker]], List[Worker]]

# Constant
wrLog = "wrLog"


class WaitArea:

    class Area_unknown_task(Exception):
        pass

    class Area_Full(Exception):
        pass

    class Area_Empty(Exception):
        pass


    def __init__(self, ident: str, specifics:  List[Tuple[str, int, int]]) -> None:
        self.ident = ident

        self._space = [(t, Queue(num), pri) for t, pri, num in specifics] \
            # type: List[Tuple[str, Queue, int]]

        # Sort Queues by priority
        self._space.sort(key = lambda t: t[2])

        # For task append puerpose only.
        self._space_map = {t: queue for t, queue, _ in self._space}

        self._num_of_tasks = 0
        self._cond = Condition()

    def enqueue(self, t: Any, timeout=None) -> None:
        try:
            q = self._space_map[type(t).__name__]
            q.put(t, timeout = timeout)

            self._num_of_tasks += 1

        except KeyError:
            raise WaitArea.Area_unknown_task
        except Full:
            raise WaitArea.Area_Full

    def dequeue(self, timeout=None) -> Any:
        with self._cond:
            cond = self._cond.wait_for(
                lambda :self._num_of_tasks > 0,
                timeout = timeout
            )

            if cond is False:
                raise WaitArea.Area_Empty

        for _, q, _ in self._space:

            try:
                task = q.get(timeout=0)
                self._num_of_tasks -= 1
                return task

            except Empty:
                pass

    def peek(self) -> Any:
        if self._num_of_tasks == 0:
            return None

        for _, q, _ in self._space:

            if len(q.queue) > 0:
                return q.queue[0]
            else:
                continue

class WorkerRoom(ModuleDaemon, Subject, Observer):

    NOTIFY_LOG = "log"
    NOTIFY_CONN = "Conn"
    NOTIFY_IN_WAIT = "Wait"
    NOTIFY_DISCONN = "Disconn"

    WAITING_INTERVAL = 300

    EVENT_CONNECTED = 0
    EVENT_DISCONNECTED = 1
    EVENT_WAITING = 2

    def __init__(self, host: str, port: int, sInst: Any) -> None:
        global M_NAME

        # Module init
        ModuleDaemon.__init__(self, M_NAME)

        # Subject init
        Subject.__init__(self, M_NAME)
        self.addType(self.NOTIFY_CONN)
        self.addType(self.NOTIFY_IN_WAIT)
        self.addType(self.NOTIFY_DISCONN)
        self.addType(self.NOTIFY_LOG)

        # Observer init
        Observer.__init__(self)

        configs = sInst.getModule(INFO_M_NAME)

        self._serverInst = sInst

        # This lock is use to protect _workers
        # while add or remove workers from it
        # Note: This lock will not protect access to a worker object
        self.lock = Lock()

        # Lock to prevent race between Waiting thread and maintain thread
        self.syncLock = Lock()

        # _workers is a collection of workers in online state
        self._workers = {}  # type: Dict[str, Worker]

        # _workers_waiting is a collection of workers in waiting state
        # if a worker which in this collection exceed WAIT limit it will
        # be removed
        self._workers_waiting = {}  # type: Dict[str, Worker]
        self.numOfWorkers = 0

        self._eventQueue = Queue(256)  # type: Queue

        self._lisAddr = ("", 0)

        self._host = host
        self._port = port

        self._WAITING_INTERVAL = configs.getConfig('WaitingInterval')
        if self._WAITING_INTERVAL == "":
            self._WAITING_INTERVAL = WorkerRoom.WAITING_INTERVAL

        self._stableThres = self._WAITING_INTERVAL + 3

        self._isPManager_init = False
        self._pManager = PostManager([], RandomElectProtocol())

        self._lastChangedPoint = datetime.utcnow()

        self._lastCandidates = []  # type: List[str]

    def begin(self) -> None:
        return None

    def cleanup(self) -> None:
        return None

    def sockSetup(self, sock: socket.socket) -> None:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 5)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 1)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 1)

    def _WR_LOG(self, msg: str) -> None:
        self.notify(WorkerRoom.NOTIFY_LOG, (wrLog, msg))

    def run(self) -> None:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((self._host, self._port))
        self.sock.listen(5)

        # Spawn a thread which respond to worker maintain
        spawnThread(lambda wr: wr.maintain(), self)

        while True:
            (workersocket, address) = self.sock.accept()
            self._WR_LOG("A new connection(" + str(address)
                         + ") has been accepted")

            self.sockSetup(workersocket)
            self._WR_LOG("Socket options set up")

            try:
                acceptedWorker = Worker(workersocket, address)
                acceptedWorker.active()

                ident = acceptedWorker.getIdent()

                self._WR_LOG("Worker " + ident + " initialized success")

            except WorkerInitFailed:
                self._WR_LOG("Worker initialize faile and close the socket")
                workersocket.shutdown(socket.SHUT_RDWR)
                continue

            if self.isExists(ident):
                workersocket.close()
                self._WR_LOG("Worker " + ident +
                             " is already exist in WorkerRoom")
                continue

            with self.syncLock:
                if ident in self._workers_waiting:
                    # fixme: socket of workerInWait is broken need to
                    # change to acceptedWorker
                    workerInWait = self._workers_waiting[ident]

                    # Update worker's status.
                    workerInWait.sockSet(acceptedWorker.sockGet())

                    arrived_addr, arrived_port = acceptedWorker.getAddress()
                    old_addr, old_port = workerInWait.getAddress()

                    # Note: Need to setup worker's status before listener
                    #       address update otherwise
                    #       listener itself will unable
                    #       to know address changed.
                    workerInWait.setAddress((arrived_addr, arrived_port))
                    workerInWait.setState(Worker.STATE_ONLINE)

                    # Move worker from waiting to online list.
                    self.addWorker(workerInWait)
                    del self._workers_waiting[ident]

                    if self._pManager.isListener(workerInWait.getIdent()):
                        if arrived_addr != old_addr:
                            # Broadcast command to all workers that online.
                            #
                            # Note: This update command will only broadcast
                            #       to workers that in online state. These
                            #       worker that in waiting state can acquire
                            #       new address via request.
                            cmd = LisAddrUpdateCmd(arrived_addr, arrived_port)
                            self.broadcast(cmd)

                    self.notify(WorkerRoom.NOTIFY_CONN, workerInWait)

                    # Send an accept command to the worker
                    # so it able to transfer message.
                    workerInWait.control(AcceptCommand())

                    if workerInWait.role is None:
                        self._pManager.addCandidate(workerInWait)

                    self._WR_LOG("Worker " + ident + " is reconnect")
                    continue

                # Need to reset the accepted worker
                # before it transfer any messages.
                acceptedWorker.control(AcceptRstCommand())

                self.addWorker(acceptedWorker)
                self._pManager.addCandidate(acceptedWorker)

                self.notify(WorkerRoom.NOTIFY_CONN, acceptedWorker)

    def isStable(self) -> bool:
        diff = (datetime.utcnow() - self._lastChangedPoint).seconds
        return diff >= self._stableThres

    def setStableThres(self, thres: int) -> None:
        self._stableThres = thres

    def _changePoint(self) -> None:
        self._lastChangedPoint = datetime.utcnow()

    def msgToPostManager(self, l: CmdResponseLetter) -> None:
        self._pManager.proto_msg_transfer(l)

    def postRelations(self) -> Tuple[str, List[str]]:
        return self._pManager.relations()

    def postListener(self) -> Optional[Worker]:
        return self._pManager.getListener()

    def getTaskOfWorker(self, wId: str, tid: str) -> Optional[Task]:
        worker = self.getWorker(wId)
        if worker is None:
            return None
        else:
            task = worker.searchTask(tid)

        return task

    def removeTaskFromWorker(self, wId: str, tid: str) -> None:
        worker = self.getWorker(wId)
        if worker is None:
            return None
        else:
            worker.removeTask(tid)

    # while eventlistener notify that a worker is disconnected
    # just change it's state into waiting wait <waiting_interval>
    # minutes if the workers is still disconnected then change
    # it's state into disconnected and wait several seconds
    # and remove from WorkerRoom
    #
    # Caution: Calling of hooks is necessary while a worker's state is changed
    def maintain(self) -> None:

        while True:
            self._waiting_worker_update()
            self._waiting_worker_processing(self._workers_waiting)
            self._postProcessing()

            time.sleep(0.01)

    def _postProcessing(self) -> None:

        candidates = [c.getIdent() for c in self._pManager.candidates()]
        if candidates != self._lastCandidates:
            self._WR_LOG("Role:" + str(self.postRelations()))
            self._WR_LOG("Candidates" + str(candidates))
            self._lastCandidates = candidates

        if not self.isStable():
            return None

        # Init postManager
        if self._isPManager_init is False:
            self._pManager.proto_init()
            self._isPManager_init = True
        else:
            # Stepping
            self._pManager.proto_step()

    def _waiting_worker_update(self) -> None:
        try:
            (eventType, index) = self._eventQueue.get(timeout=1)
        except Empty:
            return None

        if isinstance(index, str):
            # Via Worker Ident
            worker = self.getWorker(index)
        elif isinstance(index, int):
            # Via Fd in worker
            worker = self.getWorkerViaFd(index)

        if worker is None:
            return None

        ident = worker.getIdent()

        if eventType == WorkerRoom.EVENT_DISCONNECTED:
            self._WR_LOG("Worker " + ident +
                         " is disconnected changed state into Waiting")

            with self.syncLock:
                # Update worker's counter
                worker.setState(Worker.STATE_WAITING)
                self.removeWorker(ident)

                if worker.role is None:
                    # Worker is a candidate
                    self._pManager.removeCandidate(ident)

                self._workers_waiting[ident] = worker

                self.notify(WorkerRoom.NOTIFY_IN_WAIT, worker)

    def _waiting_worker_processing(self, workers: Dict[str, Worker]) -> None:
        workers_list = list(workers.values())

        if len(workers) == 0:
            return None

        outOfTime = list(
            filter(
                lambda w: w.waitCounter() > self._WAITING_INTERVAL,
                workers_list
            )
        )

        with self.syncLock:
            for worker in outOfTime:
                ident = worker.getIdent()
                self._WR_LOG("Worker " + ident +
                             " is dissconnected for a \
                             long time will be removed")
                worker.setState(Worker.STATE_OFFLINE)

                if worker.role is None:
                    # Worker is a candidate
                    self._pManager.removeCandidate(ident)
                else:
                    # Remove this worker from PostManager
                    # if it's also a listener then set listener to None
                    if self._pManager.isListener(ident):

                        # Send command to notify workers that the listener
                        # is lost.
                        self.broadcast(LisLostCommand())

                        self._pManager.setListener(None)
                        self._pManager.removeCandidate(ident)

                    self._pManager.removeProvider(ident)

                self.notify(WorkerRoom.NOTIFY_DISCONN, worker)
                del self._workers_waiting[ident]

    def notifyEvent(self, eventType: EVENT_TYPE, ident: str) -> None:
        self._eventQueue.put((eventType, ident))

    def notifyEventFd(self, eventType: EVENT_TYPE, fd: int) -> None:
        self._eventQueue.put((eventType, fd))

    def getWorkerViaFd(self, fd: int) -> Optional[Worker]:
        workers = list(self._workers.values())
        theWorker = list(filter(lambda w: w.sock.fileno() == fd, workers))

        if len(theWorker) == 0:
            return None

        return theWorker[0]

    def getWorker(self, ident: str) -> Optional[Worker]:
        with self.lock:
            if ident not in self._workers:
                return None

            return self._workers[ident]

    def getWorkerWithCond(self, condRtn: filterFunc) -> List[Worker]:
        with self.lock:
            workerList = list(self._workers.values())
            return condRtn(workerList)

    def getWorkers(self) -> List[Worker]:
        return list(self._workers.values())

    def addWorker(self, w: Worker) -> State:
        ident = w.getIdent()
        with self.lock:
            if ident in self._workers:
                return Error

            self._workers[ident] = w
            self.numOfWorkers += 1
            self._changePoint()

            return Ok

    def isExists(self, ident: str) -> bool:
        if ident in self._workers:
            return True
        else:
            return False

    def getNumOfWorkers(self) -> int:
        return self.numOfWorkers

    def getNumOfWorkersInWait(self) -> int:
        return len(self._workers_waiting)

    def broadcast(self, command: Command) -> None:
        for w in self._workers.values():
            w.control(command)

    def control(self, ident: str, command: Command) -> State:
        try:
            self._workers[ident].control(command)
        except KeyError:
            return Error
        except BrokenPipeError:
            return Error

        return Ok

    def do(self, ident: str, t: Task) -> State:
        try:
            self._workers[ident].do(t)
        except KeyError:
            return Error
        except BrokenPipeError:
            return Error

        return Ok

    def removeWorker(self, ident: str) -> State:
        with self.lock:
            if ident not in self._workers:
                return Error

            del self._workers[ident]
            self.numOfWorkers -= 1
            self._changePoint()

        return Ok

    def tasks_clear(self) -> None:
        """ Remove all failure tasks from all workers """
        for w in self._workers.values():
            w.removeTaskWithCond(lambda t: t.isFailure())

    # Content of dictionary:
    # { PropertyName:PropertyValue }
    # e.g { "max":0, "sock":ref, "processing":0,
    #       "inProcTask":ref, "ident":name }
    def statusOfWorker(self, ident: str) -> Dict:
        worker = self.getWorker(ident)

        if worker is None:
            return {}

        return worker.status()


class WorkerRoomUnitTest(TestCase):

    def test_waitarea(self):

        type_of_tasks = [("Single", 1, 10), ("Post", 0, 10)]
        area = WaitArea("Area", type_of_tasks)

        class Single:
            def __init__(self, ident: str):
                self.ident = ident

        class Post:
            def __init__(self, ident: str):
                self.ident = ident

        class Broken:
            def __init__(self, ident: str):
                self.ident = ident

        area.enqueue(Single("S1"))
        area.enqueue(Post("P1"))

        try:
            area.enqueue(Broken("B1"))

            # Exception should throw before this
            # expression.
            self.assertTrue(False)

        except WaitArea.Area_unknown_task:
            pass

        # Higher priority of tasks should
        # dequeue before lower tasks.
        p1 = area.peek()
        self.assertEqual("P1", p1.ident)
        t1 = area.dequeue()
        self.assertTrue(t1 is p1)

        s1 = area.peek()
        self.assertEqual("S1", s1.ident)
        t2 = area.dequeue()
        self.assertTrue(t2 is s1)

        i = 0
        while i < 10:
            area.enqueue(Single("S"+str(i)))
            area.enqueue(Post("P"+str(i)))
            i += 1

        # Now Single queue of area is full
        try:
            area.enqueue(Single("Full"), timeout=0)
            self.assertTrue(False)
        except WaitArea.Area_Full:
            pass

        # Now Post queue of area is full
        try:
            area.enqueue(Post("Full"), timeout=0)
            self.assertTrue(False)
        except WaitArea.Area_Full:
            pass

        i = 0
        while i < 20:
            t = area.dequeue()

            if i < 10:
                self.assertTrue(type(t) is Post)
            else:
                self.assertTrue(type(t) is Single)

            i += 1

        try:
            broken = area.dequeue(timeout=0)
            self.assertTrue(False)
        except WaitArea.Area_Empty:
            pass
