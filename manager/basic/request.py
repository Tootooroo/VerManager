# MIT License
#
# Copyright (c) 2020 Gcom
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# request.py

from abc import abstractmethod, ABC
from .letter import ReqLetter


class Request(ABC):
    """
    Class to abstrac a request from worker to master
    """

    def __init__(self, ident: str, type: str, reqMsg: str = "") -> None:
        self._ident = ident
        self._type = type
        self._reqMsg = reqMsg

    def ident(self):
        return self._ident

    def type(self):
        return self._type

    def msg(self):
        return self._reqMsg

    @abstractmethod
    def toLetter(self) -> ReqLetter:
        """ Generate a ReqLetter """

    @staticmethod
    @abstractmethod
    def fromLetter(rl: ReqLetter) -> 'Request':
        """ Generate a request from a ReqLetter """


class LastLisAddrRequire(Request):
    """ A request to request last addr of listener """

    REQUEST_TYPE = "LLAR"

    def __init__(self, ident: str) -> None:
        Request.__init__(self, ident, self.REQUEST_TYPE)

    def toLetter(self) -> 'ReqLetter':
        return ReqLetter(self.ident(), self.type(), self.msg())

    @staticmethod
    def fromLetter(rl: ReqLetter) -> 'Request':
        return LastLisAddrRequire(rl.getIdent())
