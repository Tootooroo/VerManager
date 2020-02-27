# commands.py

from .letter import Letter, CommandLetter, Optional
from typing import Dict, Tuple

class toLetter_need_implemented(Exception):
    pass

class fromLetter_need_implemented(Exception):
    pass

# Command Type definitions
CMD_CONFIG_TYPE = "cmd"

# Command subType definitions
CMD_POST_SUBTYPE = "post"


class Command:

    def __init__(self, type:str, subType:str, target:str = "", content:Dict = {}) -> None:
        self.type = type
        self.subType = subType
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
        Command.__init__(self, CMD_CONFIG_TYPE, CMD_POST_SUBTYPE, content = content)

    def address(self) -> Tuple[str, int]:
        address = self.content['address']
        port = int(self.content['port'])

        return (address, port)

    def role(self) -> str:
        return self.content['role']

    def toLetter(self) -> CommandLetter:
        cmdLetter = CommandLetter(self.type, extra = self.subType, content = self.content)

        return cmdLetter

    @staticmethod
    def fromLetter(l:Letter) -> Optional['PostConfigCmd']:

        if not isinstance(l, CommandLetter):
            return None

        type = l.getHeader('type')
        subType = l.getHeader('extra')

        address = l.getContent('address')
        port = int(l.getContent('port'))
        role = l.getContent('role')

        return PostConfigCmd(address, port, role)
