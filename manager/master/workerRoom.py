# connector.py
#
# Maintain connection with workers

import asyncio
import unittest

from datetime import datetime
from manager.basic.observer import Subject, Observer
from manager.basic.type import State, Error, Ok
from manager.master.worker import Worker, WorkerInitFailed
from manager.basic.mmanager import ModuleDaemon
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

        # _workers is a collection of workers in online state
        self._workers = {}  # type: Dict[str, Worker]

        # Lock to protect _workers_waiting
        self._lock = asyncio.Lock()

        # _workers_waiting is a collection of workers in waiting state
        # if a worker which in this collection exceed WAIT limit it will
        # be removed
        self._workers_waiting = {}  # type: Dict[str, Worker]
        self.numOfWorkers = 0

        self._eventQueue = asyncio.Queue(256)  # type: asyncio.Queue

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

        self._stop = False

    async def begin(self) -> None:
        return None

    async def cleanup(self) -> None:
        return None

    async def stop(self) -> None:
        return None

    def needStop(self) -> bool:
        return False

    async def _WR_LOG(self, msg: str) -> None:
        await self.notify(WorkerRoom.NOTIFY_LOG, (wrLog, msg))

    async def _accept_workers(self, r: asyncio.StreamReader,
                              w: asyncio.StreamWriter) -> None:
        arrived_worker = Worker(r, w)

        w_ident = ""

        try:
            await arrived_worker.active()
            w_ident = arrived_worker.getIdent()

            await self._WR_LOG("Worker " + w_ident + " inited")
        except WorkerInitFailed:
            await self._WR_LOG("Worker " + w_ident + " init failed")
            w.close()
            return None

        if self.isExists(w_ident):
            w.close()
            await self._WR_LOG("Worker " + w_ident + " is already exists")

            return None

        await self._lock.acquire()

        if w_ident in self._workers_waiting:
            # fixme: socket of workerInWait is broken need to
            # change to acceptedWorker
            workerInWait = self._workers_waiting[w_ident]
            workerInWait.setStream(arrived_worker.getStream())

            old_address = workerInWait.getAddress()
            new_address = arrived_worker.getAddress()

            # Note: Need to setup worker's status before listener
            #       address update otherwise
            #       listener itself will unable
            #       to know address changed.
            workerInWait.setAddress(new_address)
            workerInWait.setState(Worker.STATE_ONLINE)

            self.addWorker(workerInWait)
            del self._workers_waiting[w_ident]

            if self._pManager.isListener(w_ident):
                if new_address != old_address:
                    # Broadcast command to all workers that online.
                    #
                    # Note: This update command will only broadcast
                    #       to workers that in online state. These
                    #       worker that in waiting state can acquire
                    #       new address via request.
                    self.broadcast(LisAddrUpdateCmd(new_address))

            self.notify(WorkerRoom.NOTIFY_CONN, workerInWait)

            # Send an accept command to the worker
            # so it able to transfer message.
            await workerInWait.control(AcceptCommand())

            if workerInWait.role is None:
                self._pManager.addCandidate(workerInWait)

            await self._WR_LOG("Worker " + w_ident + " is reconnect")

            self._lock.release()

            return None

        self._lock.release()

        # Need to reset the accepted worker
        # before it transfer any messages.
        await arrived_worker.control(AcceptRstCommand())

        self.addWorker(arrived_worker)
        self._pManager.addCandidate(arrived_worker)

        await self.notify(WorkerRoom.NOTIFY_CONN, arrived_worker)

    async def run(self) -> None:
        server = await asyncio.start_server(self._accept_workers,
                                            self._host, self._port)

        await asyncio.gather(
            server.serve_forever(),
            self._maintain()
        )

    def isStable(self) -> bool:
        diff = (datetime.utcnow() - self._lastChangedPoint).seconds
        return diff >= self._stableThres

    def setStableThres(self, thres: int) -> None:
        self._stableThres = thres

    def _changePoint(self) -> None:
        self._lastChangedPoint = datetime.utcnow()

    async def msgToPostManager(self, l: CmdResponseLetter) -> None:
        await self._pManager.proto_msg_transfer(l)

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
    async def _maintain(self) -> None:
        while True:
            print(self.postListener())
            await self._waiting_worker_update()
            await self._waiting_worker_processing(self._workers_waiting)
            await self._postProcessing()
            await asyncio.sleep(1)

    async def _postProcessing(self) -> None:
        candidates = [c.getIdent() for c in self._pManager.candidates()]
        if candidates != self._lastCandidates:
            await self._WR_LOG("Role:" + str(self.postRelations()))
            await self._WR_LOG("Candidates" + str(candidates))
            self._lastCandidates = candidates

        if not self.isStable():
            return None

        # Init postManager
        if self._isPManager_init is False:
            await self._pManager.proto_init()
            self._isPManager_init = True
        else:
            # Stepping
            await self._pManager.proto_step()

    async def _waiting_worker_update(self) -> None:
        try:
            (eventType, index) = await self._eventQueue.get_nowait()
        except asyncio.QueueEmpty:
            return None

        worker = self.getWorker(index)
        if worker is None:
            return None

        ident = worker.getIdent()

        if eventType == WorkerRoom.EVENT_DISCONNECTED:
            await self._WR_LOG("Worker " + ident +
                               " is disconnected changed state into Waiting")

            # Update worker's counter
            worker.setState(Worker.STATE_WAITING)
            self.removeWorker(ident)

            if worker.role is None:
                # Worker is a candidate
                self._pManager.removeCandidate(ident)

            self._workers_waiting[ident] = worker

            self.notify(WorkerRoom.NOTIFY_IN_WAIT, worker)

    async def _waiting_worker_processing(self,
                                         workers: Dict[str, Worker]) -> None:

        workers_list = list(workers.values())

        if len(workers) == 0:
            return None

        outOfTime = list(
            filter(
                lambda w: w.waitCounter() > self._WAITING_INTERVAL,
                workers_list
            )
        )

        await self._lock.acquire()

        for worker in outOfTime:
            ident = worker.getIdent()
            await self._WR_LOG("Worker " + ident +
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
                    await self.broadcast(LisLostCommand())

                    self._pManager.setListener(None)
                    self._pManager.removeCandidate(ident)

                self._pManager.removeProvider(ident)

            self.notify(WorkerRoom.NOTIFY_DISCONN, worker)
            del self._workers_waiting[ident]

            self._lock.release()

    async def notifyEvent(self, eventType: EVENT_TYPE, ident: str) -> None:
        self._eventQueue.put((eventType, ident))

    def getWorker(self, ident: str) -> Optional[Worker]:
        if ident not in self._workers:
            return None
        return self._workers[ident]

    def getWorkerWithCond(self, condRtn: filterFunc) -> List[Worker]:
        workerList = list(self._workers.values())
        return condRtn(workerList)

    def getWorkerWithCond_nosync(self, condRtn: filterFunc) -> List[Worker]:
        workerList = list(self._workers.values())
        return condRtn(workerList)

    def getWorkers(self) -> List[Worker]:
        return list(self._workers.values())

    def addWorker(self, w: Worker) -> State:
        ident = w.getIdent()
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

    async def broadcast(self, command: Command) -> None:
        for w in self._workers.values():
            await w.control(command)

    async def control(self, ident: str, command: Command) -> State:
        try:
            await self._workers[ident].control(command)
        except KeyError:
            return Error
        except BrokenPipeError:
            return Error

        return Ok

    async def do(self, ident: str, t: Task) -> State:
        try:
            self._workers[ident].do(t)
        except KeyError:
            return Error
        except BrokenPipeError:
            return Error

        return Ok

    def removeWorker(self, ident: str) -> State:
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
