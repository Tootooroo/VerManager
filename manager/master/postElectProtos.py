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

        providers = self.group.getProviders()

        cmd_set_provider = PostConfigCmd(host, self.__proto_port, PostConfigCmd.ROLE_PROVIDER)

        for p in providers:
            p.control(cmd_set_provider)
            l = self.waitMsg()
            print(l.toString())

            # fixme: Need to deal with failed of provider configure
            if l.getState() is CmdResponseLetter.STATE_FAILED:
                pass

            if p.role is not Role_Listener:
                p.role = Role_Provider

        self.isInit = True

        return Ok

    def __elect_listener(self) -> Tuple[State, str]:

        if self.group is None:
            return (Ok, "")

        listener = reduce(self.__random_elect, self.group)

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
        print(l.toString())

        ident = l.getIdent()
        if ident != listener.getIdent():
            print(ident + " -- " + listener.getIdent())
            return (Error, listener.getIdent())

        state = l.getState()
        if state == CmdResponseLetter.STATE_FAILED:
            print("Error:" + l.getIdent())
            return (Error, l.getIdent())

        self.group.setListener(listener)

        return (Ok, l.getIdent())


    def step(self) -> State:

        if self.isInit is False:
            return Error

        assert(self.group is not None)

        listener = self.group.getListener()

        # Listener is still online.
        if listener is not None:
            return Ok

        # Reinit
        self.__isInit = False
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
