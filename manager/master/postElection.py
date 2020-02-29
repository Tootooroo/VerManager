# postelection.py

from functools import reduce
from queue import Queue

from manager.basic.letter import CmdResponseLetter
from manager.basic.commands import PostConfigCmd
from manager.basic.type import Ok, Error, State
from manager.master.worker import Worker
from typing import List, Dict, Optional, Callable, Iterator, Any

PostRole = int
ElectProtocolRtn = Callable[['ElectGroup', Any], None]

Role_Listener = 0  # type: PostRole
Role_Provider = 1  # type: PostRole

class ElectGroup_iter(Iterator):

    def __init__(self, iter:Iterator) -> None:
        self.__iter = iter

    def __next__(self) -> Worker:
        return self.__iter.__next__()

class ElectGroup:

    def __init__(self, workers:List[Worker] = []) -> None:
        self.__providers = {}  # type: Dict[str, Worker]

        self.__listener = None  # type: Optional[Worker]

        for w in workers:
            # At begining all workers is provider
            self.__providers[w.getIdent()] = w

    def __iter__(self) -> ElectGroup_iter:
        iter = self.__providers.__iter__()
        return ElectGroup_iter(iter)

    def numOfWorkers(self) -> int:
        num_of_providers = len(self.__providers)

        if self.__listener is not None:
            return 1 + num_of_providers

        return num_of_providers

    def getListener(self) -> Optional[Worker]:
        return self.__listener

    def setRole(self, ident:str, role:PostRole) -> State:
        if ident not in self.__providers:
            return Error

        worker = self.__providers[ident]
        self.__listener = worker

        del self.__providers [ident]

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
        self.__isInit = False
        self.__group = None # type: Optional[ElectGroup]
        self.__msgQueue = Queue(256) # type: Queue[CmdResponseLetter]

    def setGroup(self, group:ElectGroup) -> None:
        self.__group = group

    def step(self) -> State:
        raise Exception

    def init(self) -> State:
        raise Exception

    def terminate(self) -> State:
        raise Exception

    def msgTransfer(self, l:CmdResponseLetter) -> None:
        self.__msgQueue.put(l)

    def waitMsg(self) -> CmdResponseLetter:
        return self.__msgQueue.get()

class PostManager:

    def __init__(self, workers:List[Worker], proto:PostElectProtocol) -> None:

        self.__eGroup = ElectGroup(workers)
        self.__eProtocol = proto

    def removeWorker(self, ident:str) -> State:
        return self.__eGroup.removeWorker(ident)

    def addWorker(self, w:Worker) -> State:
        return self.__eGroup.addWorker(w)

    def processing(self) -> None:
        pass

    def setRole(self, ident:str, role:PostRole) -> State:
        return self.__eGroup.setRole(ident, role)

    def proto_init(self) -> State:
        pass

    def proto_step(self) -> State:
        pass

    def proto_msg_transfer(self, l:CmdResponseLetter) -> None:
        self.__eProtocol.msgTransfer(l)

    def proto_terminate(self) -> State:
        pass

    # Note: We have never change state of ElectGroup. Worker's role
    #       will be seted via event handler when response of PostConfigCmd
    #       is arrived
    def elect(self) -> State:
        # Elect a listener
        listener = None

        # Elect failed
        if listener is None:
            return Error

        providers = self.__eGroup.getProviders()

        self.__eGroup.setRole(listener.getIdent(), Role_Listener)

        (host, port) = listener.getAddress()

        cmd_set_listener = PostConfigCmd(host, port, PostConfigCmd.ROLE_LISTENER)
        listener.control(cmd_set_listener)

        # In situation that there is only one worker connect to master.
        if len(providers) == 0:
            return Ok

        cmd_set_provider = PostConfigCmd(host, port, PostConfigCmd.ROLE_PROVIDER)

        for w in providers:
            w.control(cmd_set_provider)

        return Ok
