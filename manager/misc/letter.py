# letter.py
#
# How to communicate with worker ?

import socket
import json

import typing

class Letter:

    NewTask = 'new'
    TaskCancel = 'cancel'
    Response = 'response'

    # Content of propertyNotify letter is
    # { MAX: XX, PROC: XX }
    # MAX means the maximum number of task abel to process
    # PROC means the number of task is in processing
    PropertyNotify = 'notify'

    MAX_LEN = 512

    format = '{"type":"%s", "content":%s}'

    def __init__(self, type_: typing.AnyStr, content: typing.AnyStr) -> None:
        # Type of letter:
        # (1) NewTask
        # (2) TaskCancel
        self.type_ = type_

        # content field is a dictionary
        self.content = content

    # Generate a json string
    def toString(self) -> typing.AnyStr:
        # length of content after length
        letter = Letter.format % (self.type_, str(self.content))
        letter = str(len(letter)) + letter
        return letter

    def json2Letter(s: typing.AnyStr):
        dict_ = None

        begin = s.find('{')
        dict_ = json.loads(s[begin:])

        return Letter(dict_['type'], dict_['content'])

    def typeOfLetter(self) -> typing.AnyStr:
        return self.type_

    def getContent(self, key: typing.AnyStr) -> typing.AnyStr:
        return self.content[key]

    # PropertyNotify letter interface
    def propNotify_MAX(self) -> int:
        return self.content['MAX']
    def propNotify_PROC(self) -> int:
        return int(self.content['PROC'])
