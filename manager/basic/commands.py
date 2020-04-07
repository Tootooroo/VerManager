# commands.py

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

class Command:

    def __init__(self, type:str, target:str = "", content:Dict = {}) -> None:
        self.type = type
        self.content = content
        self.target = target

    def toLetter(self) -> Letter:
        raise toLetter_need_implemented

    @staticmethod
    def fromLetter(l:CommandLetter) -> Optional['Command']:
        raise fromLetter_need_implemented


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
