# commands.py

from abc import ABC, abstractmethod
from .letter import Letter, CommandLetter, Optional
from typing import Dict, Tuple

class toLetter_need_implemented(Exception):
    pass

class fromLetter_need_implemented(Exception):
    pass

# Command subType definitions
CMD_POST_TYPE = "post"
CMD_ACCEPT = "accept"
CMD_ACCEPT_RST = "accept_rst"
CMD_LIS_ADDR_UPDATE = "lis_addr_update"
CMD_REWORK_TASK = "REWORK"
CMD_CLEAN = "CLEAN"

class Command:

    def __init__(self, type:str, target:str = "", content:Dict = {}) -> None:
        self.type = type
        self.content = content
        self.target = target

    @abstractmethod
    def toLetter(self) -> Letter:
        """ Transfer Command to Letter """

    @staticmethod
    def fromLetter(l:CommandLetter) -> Optional['Command']:
        """ Transfer from CommandLetter to Command """


class PostConfigCmd(Command):

    ROLE_LISTENER = "L"
    ROLE_PROVIDER = "P"

    def __init__(self, address:str, port:int, role:str) -> None:
        global CMD_CONFIG_TYPE, CMD_POST_SUBTYPE

        content = {'address':address, 'port':str(port), 'role':role}
        Command.__init__(self, CMD_POST_TYPE, content = content)

    def address(self) -> Tuple[str, int]:
        address = self.content['address']
        port = int(self.content['port'])

        return (address, port)

    def role(self) -> str:
        return self.content['role']

    def toLetter(self) -> CommandLetter:
        cmdLetter = CommandLetter(self.type, content = self.content)

        return cmdLetter

    @staticmethod
    def fromLetter(l:CommandLetter) -> Optional['PostConfigCmd']:

        if not isinstance(l, CommandLetter):
            return None

        address = l.getContent('address')
        port = int(l.getContent('port'))
        role = l.getContent('role')


        return PostConfigCmd(address, port, role)

class AcceptCommand(Command):

    def __init__(self) -> None:
        Command.__init__(self, CMD_ACCEPT, content = {})

    def toLetter(self) -> CommandLetter:
        cmdLetter = CommandLetter(self.type, content = self.content)
        return cmdLetter

    @staticmethod
    def fromLetter(l:CommandLetter) -> Optional['AcceptCommand']:

        if not isinstance(l, CommandLetter):
            return None

        return AcceptCommand()

class AcceptRstCommand(Command):

    def __init__(self) -> None:
        Command.__init__(self, CMD_ACCEPT_RST, content= {})

    def toLetter(self) -> CommandLetter:
        cmdLetter = CommandLetter(self.type, content = self.content)
        return cmdLetter

    @staticmethod
    def fromLetter(l:CommandLetter) -> Optional['AcceptRstCommand']:

        if not isinstance(l, CommandLetter):
            return None

        return AcceptRstCommand()

class LisAddrUpdateCmd(Command):

    def __init__(self, address:str, port:int) -> None:
        content = {"address":address, "port":port}
        Command.__init__(self, CMD_LIS_ADDR_UPDATE, content = content)

        self._address = address
        self._port = port

    def address(self) -> str:
        return self._address

    def port(self) -> int:
        return self._port

    def toLetter(self) -> CommandLetter:
        cmdLetter = CommandLetter(self.type, content = self.content)
        return cmdLetter

    @staticmethod
    def fromLetter(l:CommandLetter) -> Optional['LisAddrUpdateCmd']:
        if not isinstance(l, CommandLetter):
            return None

        return LisAddrUpdateCmd(l.getContent('address'), int(l.getContent('port')))

class ReWorkCommand(Command):
    """
    Command to tell to worker that a task need to redo.
    """

    def __init__(self, tid:str) -> None:
        content = {"tid":tid}
        Command.__init__(self, CMD_REWORK_TASK, content = content)

        self._tid = tid

    def tid(self) -> str:
        return self._tid

    def toLetter(self) -> CommandLetter:
        return CommandLetter(self.type, content = self.content)

    @staticmethod
    def fromLetter(l:CommandLetter) -> Optional['ReWorkCommand']:

        if not isinstance(l, CommandLetter):
            return None

        tid = l.getContent('tid')
        if tid == "":
            return None

        return ReWorkCommand(tid)


class CleanCommand(Command):
    """
    Command to clean tmp file generated by
    process of task on worker.
    """

    def __init__(self, tid: str) -> None:
        content = {"tid":tid}
        Command.__init__(self, CMD_CLEAN, content = content)

        self._tid = tid

    def tid(self) -> str:
        return self._tid

    def toLetter(self) -> CommandLetter:
        return CommandLetter(self.type, content = self.content)

    @staticmethod
    def fromLetter(l:CommandLetter) -> Optional['CleanCommand']:

        if not isinstance(l, CommandLetter):
            return None

        tid = l.getContent('tid')
        if tid == "":
            return None

        return CleanCommand(tid)
