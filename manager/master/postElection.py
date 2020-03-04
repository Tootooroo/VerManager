# postelection.py

from functools import reduce
from queue import Queue

from manager.basic.letter import CmdResponseLetter
from manager.basic.commands import PostConfigCmd
from manager.basic.type import Ok, Error, State
from manager.master.worker import Worker
from typing import List, Dict, Optional, Callable, \
    Iterator, Any, Tuple

PostRole = int
ElectProtocolRtn = Callable[['ElectGroup', Any], None]

Role_Listener = 0  # type: PostRole
Role_Provider = 1  # type: PostRole

class ElectGroup_iter(Iterator):

    def __init__(self, iter:Iterator, dict:Dict) -> None:
        self.__iter = iter
        self.__dict = dict

    def __next__(self) -> Worker:
        ident = self.__iter.__next__()
        return self.__dict[ident]

class ElectGroup:

    def __init__(self, workers:List[Worker] = []) -> None:
        self.__listener = None  # type: Optional[Worker]
        self.__providers = {}  # type: Dict[str, Worker]

        for w in workers:
            # At begining all workers is provider
            self.__providers[w.getIdent()] = w

    def __iter__(self) -> ElectGroup_iter:
        workers = self.__providers.copy()

        if self.__listener is not None:
            workers[self.__listener.getIdent()] = self.__listener

        iter = workers.__iter__()
        return ElectGroup_iter(iter, workers)

    def numOfWorkers(self) -> int:
        num_of_providers = len(self.__providers)

        if self.__listener is not None:
            return 1 + num_of_providers

        return num_of_providers

    def getListener(self) -> Optional[Worker]:
        return self.__listener

    def setRole(self, ident:str, role:PostRole) -> State:
        # The worker is a listener
        if ident not in self.__providers:
            if self.__listener is None:
                return Error

            listener_ident = self.__listener.getIdent()

            if ident != listener_ident:
                return Error
            else:

                if role == Role_Listener:
                    self.__listener.role = Role_Listener
                else:
                    self.__listener.role = Role_Provider
                    self.__providers[listener_ident] = self.__listener
                    self.__listener = None
        else:
            # The worker in a provider
            worker = self.__providers[ident]

            if role == Role_Listener:
                worker.role = Role_Listener

                if self.__listener is not None:
                    l_ident = self.__listener.getIdent()
                    self.__providers[l_ident] = self.__listener

                self.__listener = worker
                del self.__providers [worker.getIdent()]
            else:
                worker.role = Role_Provider

        return Ok

    def removeWorker(self, ident:str) -> State:

        # If the removed worker is listener
        if self.__listener is not None:
            ident_listener = self.__listener.getIdent()

            if ident == ident_listener:
                self.__listener = None

                return Ok

        # If the removed worker is provider
        if ident not in self.__providers:
            return Error

        del self.__providers[ident]

        return Ok

    def addWorker(self, w:Worker) -> State:
        ident = w.getIdent()

        if  ident in self.__providers:
            return Error

        self.__providers[ident] = w

        return Ok

    def getProviders(self) -> List[Worker]:

        if self.__listener is None:
            return list(self.__providers.values())

        listener_ident = self.__listener.getIdent()
        worker_list = list(self.__providers.values())

        providers = list(filter(lambda w: w.getIdent() != listener_ident, worker_list))

        return providers

    def getProvider(self, ident:str) -> Optional[Worker]:
        if ident not in self.__providers:
            return None

        return self.__providers[ident]

    def isExists(self, ident:str) -> bool:
        return ident in self.__providers

class PostElectProtocol:

    def __init__(self) -> None:
        self.isInit = False
        self.group = None # type: Optional[ElectGroup]
        self.msgQueue = Queue(256) # type: Queue[CmdResponseLetter]

    def setGroup(self, group:ElectGroup) -> None:
        self.group = group

    def step(self) -> State:
        raise Exception

    def init(self) -> State:
        raise Exception

    def terminate(self) -> State:
        raise Exception

    def msgTransfer(self, l:CmdResponseLetter) -> None:
        self.msgQueue.put(l)

    def waitMsg(self) -> CmdResponseLetter:
        return self.msgQueue.get()

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

    def __init__(self, workers:List[Worker], proto:PostElectProtocol) -> None:

        self.__eGroup = ElectGroup(workers)
        self.__eProtocol = proto

        self.__eProtocol.group = self.__eGroup

    def removeWorker(self, ident:str) -> State:
        return self.__eGroup.removeWorker(ident)

    def addWorker(self, w:Worker) -> State:
        return self.__eGroup.addWorker(w)

    def setRole(self, ident:str, role:PostRole) -> State:
        return self.__eGroup.setRole(ident, role)

    def proto_init(self) -> State:
        return self.__eProtocol.init()

    def proto_step(self) -> State:
        return self.__eProtocol.step()

    def proto_msg_transfer(self, l:CmdResponseLetter) -> None:
        self.__eProtocol.msgTransfer(l)

    def proto_terminate(self) -> State:
        return self.__eProtocol.terminate()

    def relations(self) -> Tuple[str, List[str]]:
        return self.__eProtocol.relations()

    def getListener(self) -> Optional[Worker]:
        return self.__eGroup.getListener()
