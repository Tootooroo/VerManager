# letter.py
#
# How to communicate with worker ?

import json

from typing import Optional, Dict, \
    Any, List, Union, Tuple, Callable

def newTaskLetterValidity(letter:  'Letter') -> bool:
    isHValid = letter.getHeader('ident') != "" and letter.getHeader('tid') != ""
    isCValid = letter.getContent('sn') != "" and \
               letter.getContent('vsn') != ""

    return isHValid and isCValid

def responseLetterValidity(letter:  'Letter') -> bool:
    isHValid = letter.getHeader('ident') != "" and letter.getHeader('tid') != ""
    isCValid = letter.getContent('state') != ""

    return isHValid and isCValid

def propertyLetterValidity(letter:  'Letter') -> bool:
    isHValid = letter.getHeader('ident') != ""
    isCValid = letter.getContent('MAX') != "" and letter.getContent('PROC') != ""

    return isHValid and isCValid

def binaryLetterValidity(letter:  'Letter') -> bool:
    isHValid = letter.getHeader('tid') != ""
    isCValid = letter.getContent('bytes') != ""

    return isHValid and isCValid

def logLetterValidity(letter:  'Letter') -> bool:
    isHValid = letter.getHeader('logId') != ""
    isCValid = letter.getContent('logMsg') != ""

    return isHValid and isCValid

def logRegisterLetterValidity(letter:  'Letter') -> bool:
    isHValid = letter.getHeader('logId') != ""

    return isHValid

class Letter:

    # Format of NewTask letter
    # Type    :  'new'
    # header  :  '{"tid": "...", "parent": "...", "needPost": "true/false", "menu": "..."}'
    # content :  '{"sn": "...", "vsn": "...", "datetime": "...", "extra": {...}}"
    NewTask = 'new'

    # Format of Menu letter
    # Type    :  "menu"
    # header  :  "{"mid": "..."}"
    # content :  "{"cmds": "[...]", "depends": "[...]", "output": "..."}"
    NewMenu = 'menu'

    # Format of Command letter
    # Type    :  "command"
    # header  :  "{"type": "...", "target": "...", "extra": "..."}"
    # content :  "{"content": "..."}"
    #
    # Type:
    # (1) Stop -- stop worker process
    # (2) Cancel -- Cancel target task
    # (3) Config -- Informations that guid worker how to configure itself
    Command = 'command'

    # Format of Command response letter
    # Type    :  "cmdResponse"
    # Header  :  "{"ident": "WorkerName", "type": "cmdType", "state": "...", "target": "..."}"
    # Content :  "{}"
    CmdResponse = "cmdResponse"

    # Format of TaskCancel letter
    # Type    :  'cancel'
    # header  :  '{"tid": "...", "parent": "..."}'
    # content :  '{}'
    TaskCancel = 'cancel'

    # Format of Response letter
    # Type    :  'response'
    # header  :  '{"ident": "...", "tid": "...", "parent": "..."}
    # content :  '{"state": "..."}
    Response = 'response'

    RESPONSE_STATE_PREPARE = "0"
    RESPONSE_STATE_IN_PROC = "1"
    RESPONSE_STATE_FINISHED = "2"
    RESPONSE_STATE_FAILURE = "3"

    # Format of PrpertyNotify letter
    # Type    :  'notify'
    # header  :  '{"ident": "..."}'
    # content :  '{"MAX": "...", "PROC": "..."}'
    PropertyNotify = 'notify'

    # Format of binary letter in a stream
    # | Type (2Bytes) 00001 : :  Int | Length (4Bytes) : :  Int | fileName (32 Bytes)
    # | TaskId (64Bytes) : :  String | Parent (64 Bytes) : :  String
    # | Menu (30 Bytes) : :  String | Content |
    # Format of BinaryFile letter
    # Type    :  'binary'
    # header  :  '{"tid": "...", "parent": "..."}'
    # content :  "{"bytes": b"..."}"
    BinaryFile = 'binary'

    # Format of log letter
    # Type :  'log'
    # header :  '{"ident": "...", "logId": "..."}'
    # content:  '{"logMsg": "..."}'
    Log = 'log'

    # Format of LogRegister letter
    # Type    :  'LogRegister'
    # header  :  '{"ident": "...", "logId"}'
    # content :  "{}"
    LogRegister = 'logRegister'

    BINARY_HEADER_LEN = 196
    BINARY_MIN_HEADER_LEN = 6

    MAX_LEN = 512

    format = '{"type": "%s", "header": %s, "content": %s}'

    def __init__(self, type_:  str,
                 header:  Dict[str, str] = {},
                 content:  Dict[str, Any] = {}) -> None:

        self.type_ = type_

        # header field is a dictionary
        self.header = header

        # content field is a dictionary
        self.content = content

        #if not self.validity():
        #    print(self.type_ + str(self.header) + str(self.content))

    # Generate a json string
    def toString(self) -> str:
        # length of content after length
        headerStr = str(self.header).replace("'", "\"")
        contentStr = str(self.content).replace("'", "\"")
        return Letter.format % (self.type_, headerStr, contentStr)

    def toJson(self) -> Dict:
        jsonStr = self.toString()
        return json.loads(jsonStr)

    def toBytesWithLength(self) -> bytes:
        str = self.toString()
        bStr = str.encode()

        return len(bStr).to_bytes(2, "big") + bStr

    @staticmethod
    def json2Letter(s:  str) -> 'Letter':
        dict_ = None

        begin = s.find('{')
        dict_ = json.loads(s[begin: ])

        return Letter(dict_['type'], dict_['header'], dict_['content'])

    def typeOfLetter(self) -> str:
        return self.type_

    def getHeader(self, key:  str) -> str:
        if key in self.header:
            return self.header[key]
        else:
            return ""

    def addToHeader(self, key:  str, value:  str) -> None:
        self.header[key] = value

    def setHeader(self, key: str, value: str) -> None:
        self.header[key] = value

    def setContent(self, key: str, value: Union[str, bytes]) -> None:
        self.content[key] = value

    def addToContent(self, key:  str, value:  str) -> None:
        self.content[key] = value

    def getContent(self, key:  str) -> Any:
        if key in self.content:
            return self.content[key]
        else:
            return ""

    # If a letter is received completely return 0 otherwise return the remaining bytes
    @staticmethod
    def letterBytesRemain(s:  bytes) -> int:
        # Need at least BINARY_MIN_HEADER_LEN bytes to parse
        if len(s) < Letter.BINARY_MIN_HEADER_LEN:
            return Letter.MAX_LEN

        if int.from_bytes(s[: 2], "big") == 1:
            length = int.from_bytes(s[2: 6], "big")
            return length - (len(s) - Letter.BINARY_HEADER_LEN)
        else:
            length = int.from_bytes(s[: 2], "big")
            return length - (len(s) - 2)

    @staticmethod
    def parse(s :  bytes) -> Optional['Letter']:
        # Need at least BINARY_MIN_HEADER_LEN bytes to parse
        if len(s) < Letter.BINARY_MIN_HEADER_LEN:
            return None

        # To check that is BinaryFile type or another
        if int.from_bytes(s[: 2], "big") == 1:
            return BinaryLetter.parse(s)
        else:
            return Letter.__parse(s)

    @staticmethod
    def __parse(s:  bytes) -> Optional['Letter']:
        letter = s[2: ].decode()
        dict_ = json.loads(letter)

        type_ = dict_['type']

        return parseMethods[type_].parse(s)

    def validity(self) -> bool:
        type = self.typeOfLetter()
        return validityMethods[type](self)

    # PropertyNotify letter interface
    def propNotify_MAX(self) -> int:
        return int(self.content['MAX'])
    def propNotify_PROC(self) -> int:
        return int(self.content['PROC'])
    def propNotify_IDENT(self) -> str:
        return self.header['ident']

def bytesDivide(s: bytes) -> Tuple:
    letter = s[2: ].decode()
    dict_ = json.loads(letter)

    type_ = dict_['type']
    header = dict_['header']
    content = dict_['content']

    return (type_, header, content)

class NewLetter(Letter):

    def __init__(self, tid: str, sn: str,
                 vsn: str, datetime: str,
                 menu: str = "",
                 parent: str = "",
                 extra: Dict = {},
                 needPost: str = "") -> None:
        Letter.__init__(
            self,
            Letter.NewTask,
            {"tid": tid, "parent": parent, "needPost": needPost, "menu": menu},
            {"sn": sn, "vsn": vsn, "datetime": datetime, "extra": extra}
        )

    @staticmethod
    def parse(s: bytes) -> Optional['NewLetter']:

        (type_, header, content) = bytesDivide(s)

        if type_ != Letter.NewTask:
            return None

        return NewLetter(
            tid = header['tid'],
            sn = content['sn'],
            vsn = content['vsn'],
            datetime = content['datetime'],
            menu = header['menu'],
            parent = header['parent'],
            extra = content['extra'],
            needPost = header['needPost'])

    def getTid(self) -> str:
        return self.getHeader('tid')

    def getParent(self) -> str:
        return self.getHeader('parent')

    def needPost(self) -> str:
        return self.getHeader('needPost')

    def getMenu(self) -> str:
        return self.getHeader('menu')

    def getSN(self) -> str:
        return self.getContent('sn')

    def getVSN(self) -> str:
        return self.getContent('vsn')

    def getDatetime(self) -> str:
        return self.getContent('datetime')

    def getExtra(self) -> str:
        return self.getContent('extra')

CmdType = int
CmdSubType = int

class CommandLetter(Letter):

    def __init__(self, type: str, target: str = "", extra: str = "", content: Dict[str, str] = {}) -> None:
        Letter.__init__(self, Letter.Command,
                        {"type": type, "target": target, "extra": extra},
                        content)

    @staticmethod
    def parse(s: bytes) -> Optional['CommandLetter']:
        (type_, header, content) = bytesDivide(s)

        if type_ != Letter.Command:
            return None

        return CommandLetter(header['type'], header['target'], header['extra'], content)

    def getType(self) -> str:
        return self.getHeader('type')

    def getTarget(self) -> str:
        return self.getHeader('target')

    def getExtra(self) -> str:
        return self.getHeader('extra')

    def content_(self, key:str) -> str:
        return self.getContent(key)

class CmdResponseLetter(Letter):

    STATE_SUCCESS = "s"
    STATE_FAILED  = "f"

    def __init__(self, wIdent: str, type: str, state: str, reason: str = "", target: str = "",
                 extra: Dict[str, str] = {})  -> None:
        Letter.__init__(self, Letter.CmdResponse,
                        {"ident": wIdent, "type": type, "state": state, "target": target},
                        {"reason": reason, "extra": extra})

    @staticmethod
    def parse(s: bytes) -> Optional['CmdResponseLetter']:
        (type_, header, content) = bytesDivide(s)

        if type_ != Letter.CmdResponse:
            return None

        return CmdResponseLetter(header['ident'], header['type'], header['state'],
                                 target = header['target'],
                                 reason = content['reason'],
                                 extra = content['extra'])

    def getIdent(self) -> str:
        return self.getHeader('ident')

    def getType(self) -> str:
        return self.getHeader('type')

    def getState(self) -> str:
        return self.getHeader('state')

    def getReason(self) -> str:
        return self.getContent('reason')

    def getTarget(self) -> str:
        return self.getHeader('target')

    def getExtra(self, key: str) -> str:
        return self.getContent('extra')[key]

class MenuLetter(Letter):

    def __init__(self, ver: str, mid: str, cmds: List[str], depends: List[str], output: str) -> None:
        Letter.__init__(self, Letter.NewMenu, {"mid": mid, "version": ver},
                        {"cmds": cmds, "depends": depends, "output": output})

    @staticmethod
    def parse(s: bytes) -> Optional['MenuLetter']:
        (type_, header, content) = bytesDivide(s)

        if type_ != Letter.NewMenu:
            return None

        return MenuLetter(header['version'], header['mid'],
                          content['cmds'], content['depends'], content['output'])

    def getVersion(self) -> str:
        return self.getHeader("version")

    def getMenuId(self) -> str:
        return self.getHeader('mid')

    def getCmds(self) -> List[str]:
        return self.getContent('cmds')

    def getDepends(self) -> List[str]:
        return self.getContent('depends')

    def getOutput(self) -> str:
        return self.getContent('output')

class ResponseLetter(Letter):

    def __init__(self, ident: str, tid: str, state: str, parent: str = "") -> None:
        Letter.__init__(
            self,
            Letter.Response,
            {"ident": ident, "tid": tid, "parent": parent},
            {"state": state}
        )

    @staticmethod
    def parse(s: bytes) -> Optional['ResponseLetter']:
        (type_, header, content) = bytesDivide(s)

        if type_ != Letter.Response:
            return None

        return ResponseLetter(
            ident = header['ident'],
            tid = header['tid'],
            state = content['state'],
            parent = header['parent']
        )

    def getIdent(self) -> str:
        return self.getHeader('ident')

    def getTid(self) -> str:
        return self.getHeader('tid')

    def getParent(self) -> str:
        return self.getHeader('parent')

    def getState(self) -> str:
        return self.getContent('state')

class PropLetter(Letter):

    def __init__(self, ident: str, max: str, proc: str) -> None:
        Letter.__init__(
            self,
            Letter.PropertyNotify,
            {"ident": ident},
            {"MAX": max, "PROC": proc}
        )

    @staticmethod
    def parse(s: bytes) -> Optional['PropLetter']:
        (type_, header, content) = bytesDivide(s)

        if type_ != Letter.PropertyNotify:
            return None

        return PropLetter(
            ident = header['ident'],
            max = content['MAX'],
            proc = content['PROC']
        )

    def getIdent(self) -> str:
        return self.getHeader('ident')

    def getMax(self) -> str:
        return self.getContent('MAX')

    def getProc(self) -> str:
        return self.getContent('PROC')

class BinaryLetter(Letter):

    def __init__(self, tid: str, bStr: bytes, menu: str = "",
                 fileName: str = "", parent: str = "",
                 last: str = "false") -> None:

        Letter.__init__(
            self,
            Letter.BinaryFile,
            {"tid": tid, "fileName": fileName, "parent": parent, "menu": menu},
            {"bytes": bStr}
        )

    @staticmethod
    def parse(s: bytes) -> Optional['BinaryLetter']:
        fileName = s[6: 38].decode().replace(" ", "")
        tid = s[38: 102].decode().replace(" ", "")
        parent = s[102: 166].decode().replace(" ", "")
        menu = s[166: 196].decode().replace(" ", "")
        content = s[196: ]

        return BinaryLetter(tid, content, menu, fileName, parent = parent)

    def toBytesWithLength(self) -> bytes:

        bStr = self.binaryPack()

        if bStr is None:
            return b''

        return bStr

    def binaryPack(self) -> Optional[bytes]:
        tid = self.getHeader('tid')
        fileName = self.getHeader('fileName')
        content = self.getContent("bytes")
        parent = self.getHeader('parent')
        menu = self.getHeader('menu')

        if type(content) is str:
            return None

        tid_field = b"".join([" ".encode() for x in range(64 - len(tid))]) + tid.encode()
        parent_field = b"".join([" ".encode() for x in range(64 - len(parent))]) + parent.encode()
        name_field = b"".join([" ".encode() for x in range(32 - len(fileName))]) + fileName.encode()
        menu_field = b"".join([" ".encode() for x in range(30 - len(menu))]) + menu.encode()

        # Safe here content must not str and must a bytes
        # | Type (2Bytes) 00001 : :  Int | Length (4Bytes) : :  Int | Ext (32 Bytes) | TaskId (64Bytes) : :  String
        # | Parent(64 Bytes) : :  String | Menu (30 Bytes) : :  String | Content : :  Bytes |
        packet = (1).to_bytes(2, "big") + \
                 (len(content)).to_bytes(4, "big") + \
                 name_field + \
                 tid_field + \
                 parent_field + \
                 menu_field + \
                 content

        return packet


    def getTid(self) -> str:
        return self.getHeader('tid')

    def getFileName(self) -> str:
        return self.getHeader('fileName')

    def getParent(self) -> str:
        return self.getHeader('parent')

    def getMenu(self) -> str:
        return self.getHeader('menu')

    def getBytes(self) -> str:
        return self.getContent('bytes')

    def setBytes(self, b:bytes) -> None:
        self.setContent('bytes', b)

class LogLetter(Letter):

    def __init__(self, ident: str, logId: str, logMsg: str) -> None:
        Letter.__init__(
            self,
            Letter.Log,
            {"ident": ident, "logId": logId},
            {"logMsg": logMsg}
        )

    @staticmethod
    def parse(s: bytes) -> Optional['LogLetter']:
        (type_, header, content) = bytesDivide(s)

        if type_ != Letter.Log:
            return None

        return LogLetter(
            ident = header['ident'],
            logId = header['logId'],
            logMsg = content['logMsg']
        )

    def getIdent(self) -> str:
        return self.getHeader('ident')

    def getLogId(self) -> str:
        return self.getHeader('logId')

    def getLogMsg(self) -> str:
        return self.getContent('logMsg')

class LogRegLetter(Letter):

    def __init__(self, ident: str, logId: str) -> None:
        Letter.__init__(
            self,
            Letter.LogRegister,
            {"ident": ident, "logId": logId},
        )

    @staticmethod
    def parse(s: bytes) -> Optional['LogRegLetter']:
        (type_, header, content) = bytesDivide(s)

        if  type_ != Letter.LogRegister:
            return None

        return LogRegLetter(
            ident = header['ident'],
            logId = header['logId']
        )

    def getIdent(self) -> str:
        return self.getHeader('ident')

    def getLogId(self) -> str:
        return self.getHeader('logId')

validityMethods = {
    Letter.NewTask        : newTaskLetterValidity,
    Letter.Response       : responseLetterValidity,
    Letter.PropertyNotify : propertyLetterValidity,
    Letter.BinaryFile     : binaryLetterValidity,
    Letter.Log            : logLetterValidity,
    Letter.LogRegister    : logRegisterLetterValidity,
    Letter.NewMenu        : lambda letter:  True,
    Letter.Command        : lambda letter:  True,
    Letter.CmdResponse    : lambda letter:  True
} # type:  Dict[str, Callable]

parseMethods = {
    Letter.NewTask        : NewLetter,
    Letter.Response       : ResponseLetter,
    Letter.PropertyNotify : PropLetter,
    Letter.BinaryFile     : BinaryLetter,
    Letter.Log            : LogLetter,
    Letter.LogRegister    : LogRegLetter,
    Letter.NewMenu        : MenuLetter,
    Letter.Command        : CommandLetter,
    Letter.CmdResponse    : CmdResponseLetter
} # type:  Any
