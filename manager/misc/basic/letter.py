# letter.py
#
# How to communicate with worker ?

import socket
import json

import typing
from typing import *

def newTaskLetterValidity(letter: 'Letter') -> bool:
    isHValid = letter.getHeader('ident') != "" and letter.getHeader('tid') != ""
    isCValid = letter.getContent('sn') != "" and letter.getContent('vsn') != ""

    return isHValid and isCValid

def responseLetterValidity(letter: 'Letter') -> bool:
    isHValid = letter.getHeader('ident') != "" and letter.getHeader('tid') != ""
    isCValid = letter.getContent('state') != ""

    return isHValid and isCValid

def propertyLetterValidity(letter: 'Letter') -> bool:
    isHValid = letter.getHeader('ident') != ""
    isCValid = letter.getContent('MAX') != "" and letter.getContent('PROC') != ""

    return isHValid and isCValid

def binaryLetterValidity(letter: 'Letter') -> bool:
    isHValid = letter.getHeader('tid') != ""
    isCValid = letter.getContent('bytes') != ""

    return isHValid and isCValid

def logLetterValidity(letter: 'Letter') -> bool:
    isHValid = letter.getHeader('logId') != ""
    isCValid = letter.getContent('logMsg') != ""

    return isHValid and isCValid

def logRegisterLetterValidity(letter: 'Letter') -> bool:
    isHValid = letter.getHeader('logId') != ""

    return isHValid

class Letter:

    # Format of NewTask letter
    # Type    : 'new'
    # header  : '{"ident":"...", "tid":"..."}'
    # content : '{"sn":"...", "vsn":"..."}'
    NewTask = 'new'

    # Format of TaskCancel letter
    # Type    : 'cancel'
    # header  : '{"ident":"...", "tid":"..."}'
    # content : '{}'
    TaskCancel = 'cancel'

    # Format of Response letter
    # Type    : 'response'
    # header  : '{"ident":"...", "tid":"..."}
    # content : '{"state":"..."}
    Response = 'response'

    # Format of PrpertyNotify letter
    # Type    : 'notify'
    # header  : '{"ident":"..."}'
    # content : '{"MAX":"...", "PROC":"..."}'
    PropertyNotify = 'notify'

    # Format of binary letter in a stream
    # | Type (2Bytes) 00001 :: Int | Length (4Bytes) :: Int | TaskId (64Bytes) :: String | Content |
    # Format of BinaryFile letter
    # Type    : 'binary'
    # header  : '{"tid":"..."}
    # content : "{"bytes":b"..."}"
    BinaryFile = 'binary'

    # Format of log letter
    # Type : 'log'
    # header : '{"logId":"..."}'
    # content: '{"logMsg":"..."}'
    Log = 'log'

    # Format of LogRegister letter
    # Type    : 'LogRegister'
    # header  : '{"logId"}'
    # content : "{}"
    LogRegister = 'logRegister'

    BINARY_HEADER_LEN = 70
    BINARY_MIN_HEADER_LEN = 6

    MAX_LEN = 512

    format = '{"type":"%s", "header":%s, "content":%s}'

    def __init__(self, type_: str,
                 header: Dict[str, str] = {},
                 content: Dict[str, Union[str, bytes]] = {}) -> None:

        # Type of letter:
        # (1) NewTask
        # (2) TaskCancel
        # (3) Response
        self.type_ = type_

        # header field is a dictionary
        self.header = header

        # content field is a dictionary
        self.content = content

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

    def binaryPack(self) -> Optional[bytes]:
        if self.typeOfLetter() != Letter.BinaryFile:
            return None

        tid = self.getHeader("tid")
        content = self.getContent("bytes")

        if type(content) is str:
            return None

        tid_field = b"".join([" ".encode() for x in range(64 - len(tid))]) + tid.encode()
        # Safe here content must not str and must a bytes
        packet = (1).to_bytes(2, "big") + (len(content)).to_bytes(4, "big")\
                 + tid_field + content # type: ignore

        return packet

    @staticmethod
    def json2Letter(s: str) -> 'Letter':
        dict_ = None

        begin = s.find('{')
        dict_ = json.loads(s[begin:])

        return Letter(dict_['type'], dict_['header'], dict_['content'])

    def typeOfLetter(self) -> str:
        return self.type_

    def getHeader(self, key: str) -> str:
        if key in self.header:
            return self.header[key]
        else:
            return ""

    def addToHeader(self, key: str, value: str) -> None:
        self.header[key] = value

    def addToContent(self, key: str, value: str) -> None:
        self.content[key] = value

    def getContent(self, key: str) -> Union[bytes, str]:
        if key in self.content:
            return self.content[key]
        else:
            return ""

    # If a letter is received completely return 0 otherwise return the remaining bytes
    @staticmethod
    def letterBytesRemain(s: bytes) -> int:
        # Need at least BINARY_MIN_HEADER_LEN bytes to parse
        if len(s) < Letter.BINARY_MIN_HEADER_LEN:
            return Letter.MAX_LEN

        if int.from_bytes(s[:2], "big") == 1:
            length = int.from_bytes(s[2:6], "big")
            return length - (len(s) - Letter.BINARY_HEADER_LEN)
        else:
            length = int.from_bytes(s[:2], "big")
            return length - (len(s) - 2)

    @staticmethod
    def parse(s : bytes) -> Optional['Letter']:
        # Need at least BINARY_MIN_HEADER_LEN bytes to parse
        if len(s) < Letter.BINARY_MIN_HEADER_LEN:
            return None

        # To check that is BinaryFile type or another
        if int.from_bytes(s[:2], "big") == 1:
            return Letter.__parse_binary(s)
        else:
            return Letter.__parse(s)

    @staticmethod
    def __parse_binary(s: bytes) -> Optional['Letter']:
        tid = s[6:70].decode().replace(" ", "")
        content = s[70:]

        return Letter(Letter.BinaryFile, {"tid":tid}, {"content":content})

    @staticmethod
    def __parse(s: bytes) -> Optional['Letter']:
        letter = s[2:].decode()
        dict_ = json.loads(letter)

        return Letter(dict_['type'], dict_['header'], dict_['content'])

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


validityMethods = {
    Letter.NewTask        :newTaskLetterValidity,
    Letter.Response       :responseLetterValidity,
    Letter.PropertyNotify :propertyLetterValidity,
    Letter.BinaryFile     :binaryLetterValidity,
    Letter.Log            :logLetterValidity,
    Letter.LogRegister    :logRegisterLetterValidity
} # type: Dict[str, Callable]
