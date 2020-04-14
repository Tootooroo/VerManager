# connector.py
#
# Maintain connection with workers

import time
import socket
from datetime import datetime

from threading import Lock

from manager.basic.type import *
from manager.master.worker import Worker, WorkerInitFailed

from manager.basic.mmanager import ModuleDaemon

from queue import Queue, Empty

from manager.basic.util import spawnThread, map_strict
from manager.master.logger import Logger

from manager.basic.letter import Letter
from manager.basic.commands import Command, LisAddrUpdateCmd
from manager.master.task import Task

from manager.master.postElectProtos import RandomElectProtocol
from manager.master.postElection import PostManager, PostElectProtocol, Role_Listener, Role_Provider

from manager.basic.letter import CmdResponseLetter

from typing import *

from manager.basic.info import M_NAME as INFO_M_NAME
from manager.master.logger import M_NAME as LOGGER_M_NAME

from manager.basic.commands import AcceptCommand, AcceptRstCommand, LisAddrUpdateCmd

M_NAME = "WorkerRoom"

# Type alias
EVENT_TYPE = int
hookTuple = Tuple[Callable[[Worker, Any], None], Any]
filterFunc = Callable[[List[Worker]], List[Worker]]

# Constant
wrLog = "wrLog"

class WorkerRoom(ModuleDaemon):

    WAITING_INTERVAL = 300

    EVENT_CONNECTED = 0
    EVENT_DISCONNECTED = 1
    EVENT_WAITING = 2

    def __init__(self, host:str, port:int, sInst:Any) -> None:
        global M_NAME

        ModuleDaemon.__init__(self, M_NAME)

        configs = sInst.getModule(INFO_M_NAME)

        self.__serverInst = sInst

        # This lock is use to protect __workers
        # while add or remove workers from it
        # Note: This lock will not protect access to a worker object
        self.lock = Lock()

        # Lock to prevent race between Waiting thread and maintain thread
        self.syncLock = Lock()

        # __workers is a collection of workers in online state
        self.__workers = {}  # type: Dict[str, Worker]

        # __workers_waiting is a collection of workers in waiting state
        # if a worker which in this collection exceed WAIT limit it will
        # be removed
        self.__workers_waiting = {}  # type: Dict[str, Worker]
        self.numOfWorkers = 0

        self.__eventQueue = Queue(256) # type: Queue

        # Collection of methods to be run after a worker is accepted by WorkerRoom
        self.hooks = [] # type: List[hookTuple]

        self.waitingStateHooks = [] # type: List[hookTuple]
        self.disconnStateHooks = [] # type: List[hookTuple]

        self._lisAddr = ("", 0)

        self.__host = host
        self.__port = port

        self.__WAITING_INTERVAL = configs.getConfig('WaitingInterval')
        if self.__WAITING_INTERVAL == "":
            self.__WAITING_INTERVAL = WorkerRoom.WAITING_INTERVAL

        self.__stableThres = self.__WAITING_INTERVAL + 3

        self.__isPManager_init = False
        self.__pManager = PostManager([], RandomElectProtocol())

        self.__lastChangedPoint = datetime.utcnow()

        self._lastCandidates = [] # type: List[str]

        self.logger = None # type: Optional[Logger]

    def sockSetup(self, sock:socket.socket) -> None:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 5)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 1)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 1)

    def _WR_LOG(self, msg:str) -> None:
        if self.logger is not None:
            Logger.putLog(self.logger, wrLog, msg)
        else:
            self.logger = self.__serverInst.getModule(LOGGER_M_NAME)
            if self.logger is not None:
                self.logger.log_register(wrLog)

    def run(self) -> None:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((self.__host, self.__port))
        self.sock.listen(5)

        # Spawn a thread which respond to worker maintain
        maintainer = spawnThread(lambda wr: wr.maintain(), self)

        while True:
            (workersocket, address) = self.sock.accept()
            self._WR_LOG("A new connection(" + str(address) + ") has been accepted")

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
                self._WR_LOG("Worker " + ident + " is already exist in WorkerRoom")
                continue

            with self.syncLock:
                if ident in self.__workers_waiting:
                    # fixme: socket of workerInWait is broken need to
                    # change to acceptedWorker
                    workerInWait = self.__workers_waiting[ident]

                    # Update worker's status.
                    workerInWait.sockSet(acceptedWorker.sockGet())

                    arrived_addr, arrived_port = acceptedWorker.getAddress()
                    old_addr, old_port         = workerInWait.getAddress()

                    if arrived_addr != old_addr:
                        workerInWait.setAddress((arrived_addr, arrived_port))

                        # Broadcast command to all workers that online.
                        #
                        # Note: This update command will only broadcast
                        #       to workers that in online state. These
                        #       worker that in waiting state can acquire
                        #       new address via request.
                        cmd = LisAddrUpdateCmd(arrived_addr, arrived_port)
                        self.broadcast(cmd)

                    workerInWait.setState(Worker.STATE_ONLINE)

                    self.addWorker(workerInWait)
                    del self.__workers_waiting [ident]
                    map_strict(lambda hook: hook[0](workerInWait, hook[1]), self.hooks)

                    # Send an accept command to the worker
                    # so it able to transfer message.
                    workerInWait.control(AcceptCommand())

                    if not self.__pManager.isListener(ident):
                        self.__pManager.addCandidate(workerInWait)

                    self._WR_LOG("Worker " + ident + " is reconnect")
                    continue

                # Need to reset the accepted worker before it transfer any messages.
                acceptedWorker.control(AcceptRstCommand())

                self.addWorker(acceptedWorker)
                self.__pManager.addCandidate(acceptedWorker)

                map_strict(lambda hook: hook[0](acceptedWorker, hook[1]), self.hooks)

    def isStable(self) -> bool:
        diff = (datetime.utcnow() - self.__lastChangedPoint).seconds
        return diff >= self.__stableThres

    def setStableThres(self, thres:int) -> None:
        self.__stableThres = thres

    def __changePoint(self) -> None:
        self.__lastChangedPoint = datetime.utcnow()

    def msgToPostManager(self, l:CmdResponseLetter) -> None:
        self.__pManager.proto_msg_transfer(l)

    def postRelations(self) -> Tuple[str, List[str]]:
        return self.__pManager.relations()

    def postListener(self) -> Optional[Worker]:
        return self.__pManager.getListener()

    # while eventlistener notify that a worker is disconnected
    # just change it's state into waiting wait <waiting_interval>
    # minutes if the workers is still disconnected then change
    # it's state into disconnected and wait several seconds
    # and remove from WorkerRoom
    #
    # Caution: Calling of hooks is necessary while a worker's state is changed
    def maintain(self) -> None:

        while True:
            self.__waiting_worker_update()
            self.__waiting_worker_processing(self.__workers_waiting)
            self.__postProcessing()

            time.sleep(0.01)

    def __postProcessing(self) -> None:

        candidates = [c.getIdent() for c in self.__pManager.candidates()]
        if candidates != self._lastCandidates:
            self._WR_LOG("Role:" + str(self.postRelations()))
            self._WR_LOG("Candidates" + str(candidates))
            self._lastCandidates = candidates

        if not self.isStable():
            return None

        # Init postManager
        if self.__isPManager_init == False:
            self.__pManager.proto_init()
            self.__isPManager_init = True
        else:
            # Stepping
            self.__pManager.proto_step()

    def __waiting_worker_update(self) -> None:
        try:
            (eventType, index) = self.__eventQueue.get(timeout=1)
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

            # Update worker's counter
            worker.setState(Worker.STATE_WAITING)
            self.removeWorker(ident)

            if worker.role == None:
                # Worker is a candidate
                self.__pManager.removeCandidate(ident)

            self.__workers_waiting[ident] = worker

            map_strict(lambda hook: hook[0](worker, hook[1]), self.waitingStateHooks)

    def __waiting_worker_processing(self, workers: Dict[str, Worker]) -> None:
        workers_list = list(workers.values())

        if len(workers) == 0:
            return None

        outOfTime = list(filter(lambda w: w.waitCounter() > self.__WAITING_INTERVAL, workers_list))

        for worker in outOfTime:
            ident = worker.getIdent()
            self._WR_LOG("Worker " + ident +
                         " is dissconnected for a long time will be removed")
            worker.setState(Worker.STATE_OFFLINE)

            if worker.role == None:
                # Worker is a candidate
                self.__pManager.removeCandidate(ident)
            else:
                # Remove this worker from PostManager
                # if it's also a listener then set listener to None
                if self.__pManager.isListener(ident):
                    self.__pManager.setListener(None)
                    self.__pManager.removeCandidate(ident)
                self.__pManager.removeProvider(ident)

            map_strict(lambda hook: hook[0](worker, hook[1]), self.disconnStateHooks)

        for w in outOfTime:
            with self.syncLock:
                del self.__workers_waiting [w.getIdent()]

    def hookRegister(self, hook: hookTuple) -> None:
        self.hooks.append(hook)

    def waitingHookRegister(self, hook: hookTuple) -> None:
        self.waitingStateHooks.append(hook)

    def disconnHookRegister(self, hook: hookTuple) -> None:
        self.disconnStateHooks.append(hook)

    def notifyEvent(self, eventType: EVENT_TYPE, ident: str) -> None:
        self.__eventQueue.put((eventType, ident))

    def notifyEventFd(self, eventType: EVENT_TYPE, fd: int) -> None:
        self.__eventQueue.put((eventType, fd))

    def getWorkerViaFd(self, fd: int) -> Optional[Worker]:
        workers = list(self.__workers.values())
        theWorker = list(filter(lambda w: w.sock.fileno() == fd, workers))

        if len(theWorker) == 0:
            return None

        return theWorker[0]

    def getWorker(self, ident: str) -> Optional[Worker]:
        with self.lock:
            if not ident in self.__workers:
                return None

            return self.__workers[ident]

    def getWorkerWithCond(self, condRtn: filterFunc) -> List[Worker]:
        with self.lock:
            workerList = list(self.__workers.values())
            return condRtn(workerList)

    def getWorkers(self) -> List[Worker]:
        return list(self.__workers.values())

    def addWorker(self, w: Worker) -> State:
        ident = w.getIdent()
        with self.lock:
            if ident in self.__workers:
                return Error

            self.__workers[ident] = w
            self.numOfWorkers += 1
            self.__changePoint()

            return Ok

    def isExists(self, ident: str) -> bool:
        if ident in self.__workers:
            return True
        else:
            return False

    def getNumOfWorkers(self) -> int:
        return self.numOfWorkers

    def getNumOfWorkersInWait(self) -> int:
        return len(self.__workers_waiting)

    def broadcast(self, command:Command) -> None:
        for w in self.__workers.values():
            w.control(command)

    def control(self, ident:str, command:Command) -> State:
        try:
            self.__workers[ident].control(command)
        except KeyError:
            return Error
        except BrokenPipeError:
            return Error

        return Ok

    def do(self, ident:str, t:Task) -> State:
        try:
            self.__workers[ident].do(t)
        except KeyError:
            return Error
        except BrokenPipeError:
            return Error

        return Ok

    def removeWorker(self, ident: str) -> State:
        with self.lock:
            if not ident in self.__workers:
                return Error

            del self.__workers [ident]
            self.numOfWorkers -= 1
            self.__changePoint()

        return Ok

    # Content of dictionary:
    # { PropertyName:PropertyValue }
    # e.g { "max":0, "sock":ref, "processing":0, "inProcTask":ref, "ident":name }
    def statusOfWorker(self, ident:str) -> Dict:
        worker = self.getWorker(ident)

        if worker is None:
            return {}

        return worker.status()
