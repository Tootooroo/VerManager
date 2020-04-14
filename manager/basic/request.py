# request.py

from abc import abstractmethod, ABC
from .letter import Letter, ReqLetter

class Request(ABC):
    """
    Class to abstrac a request from worker to master
    """

    def __init__(self, ident:str, type:str, reqMsg:str = "") -> None:
        self._ident = ident
        self._type = type
        self._reqMsg = reqMsg

    def ident(self) : return self._ident

    def type(self)  : return self._type

    def msg(self)   : return self._reqMsg

    @abstractmethod
    def toLetter(self) -> ReqLetter:
        """ Generate a ReqLetter """

    @staticmethod
    @abstractmethod
    def fromLetter(rl:ReqLetter) -> 'Request':
        """ Generate a request from a ReqLetter """



class LastLisAddrRequire(Request):
    """ A request to request last addr of listener """

    REQUEST_TYPE = "LLAR"

    def __init__(self, ident:str) -> None:
        Request.__init__(self, ident, self.REQUEST_TYPE)

    def toLetter(self) -> 'ReqLetter':
        return ReqLetter(self.ident(), self.type(), self.msg())

    @staticmethod
    def fromLetter(rl:ReqLetter) -> 'Request':
        return LastLisAddrRequire(rl.getIdent())
