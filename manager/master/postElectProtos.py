# postElectProtos.py

from functools import reduce
from typing import List, Tuple

from queue import Queue
from manager.basic.type import Ok, Error, State
from manager.basic.letter import CmdResponseLetter
from manager.basic.commands import PostConfigCmd
from manager.master.worker import Worker
from manager.master.postElection import PostElectProtocol, ElectGroup, \
    Role_Listener, Role_Provider

class ELECT_PROTO_INIT_FAILED(Exception): pass

class RandomElectProtocol(PostElectProtocol):

    def __init__(self) -> None:
        PostElectProtocol.__init__(self)
        self.__blackList = [] # type: List[str]

        self.__proto_port = 8066

    def init(self) -> State:
        # __group maybe None because WorkerRoom is in instable status
        if self.group is None:
            return Error

        if self.group.numOfWorkers() is 0:
            return Error

        ret = Error

        # Listener elect
        while ret is Error:
            (ret, ident) = self.__elect_listener()

            if ret is Error:
                self.__blackList.append(ident)

                if len(self.__blackList) == self.group.numOfWorkers():
                    return Error

        # Broadcast configuration to providers
        listener = self.group.getListener()
        assert(listener is not None)

        (host, port) = listener.getAddress()

        candidates = self.group.candidateDrags()

        cmd_set_provider = PostConfigCmd(host, self.__proto_port,
                                         PostConfigCmd.ROLE_PROVIDER)

        for c in candidates:

            # Add to group as a provider
            if c.role == Role_Listener:
                self.group.addProvider(c)
                c.role = Role_Listener
            else:
                self.group.addProvider(c)

            c.control(cmd_set_provider)
            l = self.waitMsg()

            # fixme: Need to deal with failed of provider configure
            if l.getState() is CmdResponseLetter.STATE_FAILED:
                pass

        self.isInit = True

        return Ok

    def __elect_listener(self) -> Tuple[State, str]:

        if self.group is None:
            return (Ok, "")

        if self.group.numOfWorkers() == 0:
            return (Ok, "")

        candidates = self.group.candidates()

        listener = reduce(self.__random_elect, candidates)

        if listener in self.__blackList:
            return (Error, "")

        if listener is None:
            raise ELECT_PROTO_INIT_FAILED

        providers = self.group.getProviders()

        (host, port) = listener.getAddress()

        cmd_set_listener = PostConfigCmd(host, self.__proto_port,
                                         PostConfigCmd.ROLE_LISTENER)

        listener.control(cmd_set_listener)
        l = self.waitMsg()

        ident = l.getIdent()
        if ident != listener.getIdent():
            return (Error, listener.getIdent())

        state = l.getState()
        if state == CmdResponseLetter.STATE_FAILED:
            return (Error, l.getIdent())

        self.group.setListener(listener)

        return (Ok, l.getIdent())


    def step(self) -> State:

        if self.isInit is False:
            return Error

        assert(self.group is not None)

        listener = self.group.getListener()

        # Listener is still online.
        candidates = self.group.candidateDrags()

        if listener is not None:
            if candidates == []:
                return Ok
            else:
                host, port = listener.getAddress()
                for candidate in candidates:
                    self.group.addProvider(candidate)
                    cmd_set_provider = PostConfigCmd(host, self.__proto_port,
                                                     PostConfigCmd.ROLE_PROVIDER)
                    candidate.control(cmd_set_provider)
                    l = self.waitMsg()

                    if l.getState() is CmdResponseLetter.STATE_FAILED:
                        assert(False)

        # Reinit
        self.__isInit = False

        # Move all providers into candidates
        providers = self.group.getProviders()
        for provider in providers:
            provider.role = Role_Provider
            self.group.removeProvider(provider.getIdent())
            self.group.addCandidate(provider)

        self.init()

        return Ok

    def terminate(self) -> State:
        pass

    def __random_elect(self, w1:Worker, w2:Worker) -> Worker:
        ident_w1 = w1.getIdent()
        ident_w2 = w2.getIdent()

        # both w1 and w2 in blacklist
        w1_black = ident_w1 in self.__blackList
        w2_black = ident_w2 in self.__blackList

        if (w1_black and w2_black) or (not w1_black and not w2_black):
            return w1
        elif w1_black:
            return w2
        else:
            return w1
