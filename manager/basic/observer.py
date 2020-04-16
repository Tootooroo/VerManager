# observer.py

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Callable

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
        self._observers = [] # type: List[Observer]

    def subscribe(self, ob: Observer) -> None:
        if ob not in self._observers:
            self._observers.append(ob)

    def withdraw(self, ob) -> None:
        if ob in self._observers:
            self._observers.remove(ob)

    def notify(self, data:Any) -> None:
        for ob in self._observers:
            ob.update(self._subject_ident, data)
