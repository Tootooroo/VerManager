# postElectProtos.py

from functools import reduce
from typing import List, Tuple, Optional

from queue import Queue, Empty as queue_Empty
from manager.basic.type import Ok, Error, State
from manager.basic.letter import CmdResponseLetter
from manager.basic.commands import Command, PostConfigCmd
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

        if self.group.numOfCandidates() is 0:
            return Error

        ret = Error

        # Listener elect
        (ret, ident) = self.__elect_listener()
        if ret == Error:
            return Error

        # Broadcast configuration to providers
        listener = self.group.getListener()
        assert(listener is not None)

        (host, port) = listener.getAddress()

        candidates = self.group.candidateIter()

        cmd_set_provider = PostConfigCmd(host, self.__proto_port,
                                         PostConfigCmd.ROLE_PROVIDER)
        for c in candidates:
            # fixme: May cause performance problem you can
            #        send all command in onece. And wait a
            #        constant time for all response.
            l = self._send_command_and_wait(c, cmd_set_provider, timeout = 2)
            if l is None: continue

            # fixme: Need to deal with failed of provider configure
            if l.getState() is CmdResponseLetter.STATE_SUCCESS:
                # Add to group as a provider
                if c.role == Role_Listener:
                    self.group.addProvider(c)
                    c.role = Role_Listener
                else:
                    self.group.addProvider(c)

                self.group.removeCandidate_(c)

        self.isInit = True

        return Ok

    def _send_command_and_wait(self, w:Worker, cmd:Command, timeout=None) -> Optional[CmdResponseLetter]:
        try:
            w.control(cmd)
            response = self.waitMsg(timeout=timeout)

            while response.getIdent() != w.getIdent():
                response = self.waitMsg(timeout=timeout)

        except (BrokenPipeError, queue_Empty):
            return None
        except:
            import traceback
            traceback.print_exc()

            return None

        return response

    def __elect_listener(self) -> Tuple[State, str]:

        if self.group is None:
            return (Ok, "")

        if self.group.numOfCandidates() == 0:
            return (Ok, "")

        candidates = self.group.candidates()

        listener = reduce(self.__random_elect, candidates)

        if listener is None:
            raise ELECT_PROTO_INIT_FAILED

        providers = self.group.getProviders()

        (host, port) = listener.getAddress()

        cmd_set_listener = PostConfigCmd(host, self.__proto_port,
                                         PostConfigCmd.ROLE_LISTENER)

        # Clear messages trivial messages may remain in queue
        # due to failed election before.
        self.msgClear()

        l = self._send_command_and_wait(listener, cmd_set_listener, timeout=2)
        if l is None: return (Error, "")

        state = l.getState()
        if state == CmdResponseLetter.STATE_FAILED:
            return (Error, l.getIdent())

        self.group.setListener(listener)

        return (Ok, l.getIdent())


    def step(self) -> State:

        assert(self.group is not None)

        listener = self.group.getListener()

        # Listener is still online.
        candidates = self.group.candidates()

        if listener is not None:
            if candidates == []:
                return Ok
            else:
                host, _ = listener.getAddress()
                cmd_set_provider = PostConfigCmd(host, self.__proto_port,
                                                    PostConfigCmd.ROLE_PROVIDER)

                self.msgClear()

                candidates_iter = self.group.candidateIter()
                for candidate in candidates_iter:
                    l = self._send_command_and_wait(candidate, cmd_set_provider,
                                                    timeout=2)
                    if l is None: continue

                    if l.getState() is CmdResponseLetter.STATE_SUCCESS:
                        self.group.addProvider(candidate)
                        self.group.removeCandidate_(candidate)


                return Ok

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
