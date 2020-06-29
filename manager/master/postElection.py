# postelection.py

from queue import Queue, Empty as QUEUE_EMPTY

from threading import Lock
from manager.basic.util import partition
from manager.basic.letter import CmdResponseLetter
from manager.basic.type import Ok, Error, State
from manager.master.worker import Worker
from typing import List, Dict, Optional, Callable, \
    Iterator, Any, Tuple, Generator

PostRole = int
ElectProtocolRtn = Callable[['ElectGroup', Any], None]

Role_Listener = 0  # type: PostRole
Role_Provider = 1  # type: PostRole


class ElectGroup_iter(Iterator):

    def __init__(self, iter: Iterator, dict: Dict) -> None:
        self._iter = iter
        self._dict = dict

    def __next__(self) -> Worker:
        ident = self._iter.__next__()
        return self._dict[ident]


class ElectGroup:

    def __init__(self, workers: List[Worker] = []) -> None:
        self._listener = None  # type: Optional[Worker]
        self._providers = {}  # type: Dict[str, Worker]

        self._lock_c = Lock()
        self._candidate = []  # type: List[Worker]

        for w in workers:
            # At begining all workers is provider
            self._providers[w.getIdent()] = w

    def __iter__(self) -> ElectGroup_iter:
        workers = self._providers.copy()

        iter = workers.__iter__()
        return ElectGroup_iter(iter, workers)

    def numOfWorkers(self) -> int:
        num_of_providers = len(self._providers)
        return num_of_providers

    def numOfCandidates(self) -> int:
        return len(self._candidate)

    def setListener(self, lis: Optional[Worker]) -> None:
        if lis is not None:
            lis.role = Role_Listener
        self._listener = lis

    def getListener(self) -> Optional[Worker]:
        return self._listener

    def isListener(self, ident) -> bool:
        if self._listener is None:
            return False
        return ident == self._listener.getIdent()

    def removeProvider(self, ident: str) -> State:
        if ident not in self._providers:
            return Error
        del self._providers[ident]
        return Ok

    def addProvider(self, w: Worker) -> State:
        ident = w.getIdent()

        if ident in self._providers:
            return Error

        if w.role is None:
            w.role = Role_Provider

        self._providers[ident] = w
        return Ok

    def getProviders(self) -> List[Worker]:
        return list(self._providers.values())

    def getProvider(self, ident: str) -> Optional[Worker]:
        if ident not in self._providers:
            return None

        return self._providers[ident]

    def addCandidate(self, w: Worker) -> State:
        with self._lock_c:
            if w in self._candidate:
                return Error

            w.role = None
            self._candidate.append(w)

        return Ok

    def removeCandidate(self, ident: str) -> Optional[Worker]:
        with self._lock_c:
            beRemoved, remain = partition(self._candidate,
                                          lambda c: c.getIdent() == ident)

            if beRemoved == []:
                return None
            else:
                self._candidate = remain
                return beRemoved[0]

    def removeCandidate_(self, w: Worker) -> State:
        with self._lock_c:
            if w not in self._candidate:
                return Error
            else:
                self._candidate.remove(w)
                return Ok

    def candidateIter(self) -> Generator:
        for candidate in self._candidate:
            yield candidate

    def removeAllCandidates(self) -> None:
        with self._lock_c:
            for c in self._candidate:
                self._candidate.remove(c)

    def getCandidate(self, ident: str) -> Optional[Worker]:
        with self._lock_c:
            for candidate in self._candidate:
                if candidate.getIdent() == ident:
                    return candidate

        return None

    def candidates(self) -> List[Worker]:
        return self._candidate

    def isExists(self, ident: str) -> bool:
        return ident in self._providers


class PostElectProtocol:

    def __init__(self) -> None:
        self.isInit = False
        self.group = None  # type: Optional[ElectGroup]
        self.msgQueue = Queue(256)  # type: Queue[CmdResponseLetter]

    def setGroup(self, group: ElectGroup) -> None:
        self.group = group

    def step(self) -> State:
        raise Exception

    async def init(self) -> State:
        raise Exception

    def terminate(self) -> State:
        raise Exception

    def msgTransfer(self, l: CmdResponseLetter) -> None:
        self.msgQueue.put(l)

    def waitMsg(self, timeout=None) -> Optional[CmdResponseLetter]:
        try:
            return self.msgQueue.get(timeout=timeout)
        except QUEUE_EMPTY:
            return None

    def msgClear(self) -> None:
        self.msgQueue.queue.clear()

    def relations(self) -> Tuple[str, List[str]]:

        if self.group is None:
            return ("", [])

        listener = self.group.getListener()
        if listener is not None:
            listener_ident = listener.getIdent()
        else:
            listener_ident = ""

        providers = self.group.getProviders()
        providers_ident = list(map(lambda p: p.getIdent(), providers))

        return (listener_ident, providers_ident)


class PostManager:

    def __init__(self, workers: List[Worker],
                 proto: PostElectProtocol) -> None:

        self._eGroup = ElectGroup(workers)
        self._eProtocol = proto

        self._eProtocol.group = self._eGroup

    def getListener(self) -> Optional[Worker]:
        return self._eGroup.getListener()

    def setListener(self, lis: Optional[Worker]) -> None:
        self._eGroup.setListener(lis)

    def isListener(self, ident: str) -> bool:
        return self._eGroup.isListener(ident)

    def removeProvider(self, ident: str) -> State:
        return self._eGroup.removeProvider(ident)

    def addProvider(self, w: Worker) -> State:
        return self._eGroup.addProvider(w)

    def addCandidate(self, w: Worker) -> State:
        return self._eGroup.addCandidate(w)

    def removeCandidate(self, ident: str) -> Optional[Worker]:
        return self._eGroup.removeCandidate(ident)

    def getCandidate(self, ident: str) -> Optional[Worker]:
        return self._eGroup.getCandidate(ident)

    def candidates(self) -> List[Worker]:
        return self._eGroup.candidates()

    def proto_init(self) -> State:
        return self._eProtocol.init()

    def proto_step(self) -> State:
        return self._eProtocol.step()

    def proto_msg_transfer(self, l: CmdResponseLetter) -> None:
        self._eProtocol.msgTransfer(l)

    def proto_terminate(self) -> State:
        return self._eProtocol.terminate()

    def relations(self) -> Tuple[str, List[str]]:
        return self._eProtocol.relations()
