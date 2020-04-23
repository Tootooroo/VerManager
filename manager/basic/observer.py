# observer.py

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Callable, overload

class Observer(ABC):
    """
    Observer can be subscribe to Subjects so it able know changed
    of Subjects.
    """

    def __init__(self) -> None:
        self._handlers = {} #type: Dict[str, Callable[[Any], None]]

    def handler_install(self, source:str, handler:Callable[[Any], None]) -> None:
        self._handlers[source] = handler

    def handler_remove(self, source:str) -> None:
        if source in self._handlers:
            del self._handlers [source]

    def update(self, source:str, data:Any) -> None:
        """
        Called by Subject to notify observer
        """
        if source not in self._handlers:
            return None

        handler = self._handlers[source]

        handler(data)


class Subject(ABC):
    """
    Subject is a data source for observers, onece data of
    Subject is updated it will notify observer.
    """

    def __init__(self, ident:str) -> None:
        self._subject_ident = ident
        self._observers = {} # type: Dict[str, List[Observer]]

    def addType(self, type:str) -> None:
        if type in self._observers:
            return None

        self._observers[type] = []

    def removeType(self, type:str) -> None:
        if type in self._observers:
            del self._observers [type]

    def subscribe(self, type:str, ob: Observer) -> None:
        if type in self._observers:
            obs_of_type = self._observers[type]

            if ob not in obs_of_type:
                obs_of_type.append(ob)

    def withdraw(self, type:str, ob: Observer) -> None:
        if type in self._observers:

            if ob in self._observers[type]:
                self._observers[type].remove(ob)

    def withdrawAll(self, ob: Observer) -> None:
        for type in self._observers:
            obs = self._observers[type]

            if ob in obs:
                obs.remove(ob)

    def notify(self, type:str, data:Any) -> None:
        if type in self._observers:
            obs = self._observers[type]

            for ob in obs:
                ob.update(self._subject_ident, data)
