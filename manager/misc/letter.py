# letter.py
#
# How to communicate with worker ?

import socket
import json

import typing

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

    MAX_LEN = 512

    format = '{"type":"%s", "header":%s, "content":%s}'

    def __init__(self, type_: typing.AnyStr,
                 header: typing.Dict,
                 content: typing.Dict) -> None:

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
    def toString(self) -> typing.AnyStr:
        # length of content after length
        letter = Letter.format % (self.type_,
                                  str(self.header).replace("'", "\""),
                                  str(self.content).replace("'", "\""))

        letter = str(len(letter)) + letter
        return letter

    def json2Letter(s: typing.AnyStr):
        dict_ = None

        begin = s.find('{')
        dict_ = json.loads(s[begin:])

        return Letter(dict_['type'], dict_['header'], dict_['content'])

    def typeOfLetter(self) -> typing.AnyStr:
        return self.type_

    def getHeader(self, key: typing.AnyStr) -> typing.AnyStr:
        return self.header[key]

    def getContent(self, key: typing.AnyStr) -> typing.AnyStr:
        return self.content[key]

    # PropertyNotify letter interface
    def propNotify_MAX(self) -> int:
        return int(self.content['MAX'])
    def propNotify_PROC(self) -> int:
        return int(self.content['PROC'])
    def propNotify_IDENT(self) -> typing.AnyStr:
        return self.header['ident']
