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

# observer.py

from abc import ABC
from typing import List, Dict, \
    Any, Callable, Coroutine


class Observer(ABC):
    """
    Observer can be subscribe to Subjects so it able know changed
    of Subjects.
    """

    def __init__(self) -> None:
        self._handlers = {}  # type: Dict[str, Callable[[Any], Coroutine]]

    def handler_install(self, source: str,
                        handler: Callable[[Any], Coroutine]) -> None:
        self._handlers[source] = handler

    def handler_remove(self, source: str) -> None:
        if source in self._handlers:
            del self._handlers[source]

    async def update(self, src: str, data: Any) -> None:
        """
        Called by Subject to notify observer
        """
        if src not in self._handlers:
            return None

        handler = self._handlers[src]

        await handler(data)


class Subject(ABC):
    """
    Subject is a data source for observers, onece data of
    Subject is updated it will notify observer.
    """

    def __init__(self, ident: str) -> None:
        self._subject_ident = ident
        self._observers = {}  # type: Dict[str, List[Observer]]

    def addType(self, type: str) -> None:
        if type in self._observers:
            return None

        self._observers[type] = []

    def removeType(self, type: str) -> None:
        if type in self._observers:
            del self._observers[type]

    def subscribe(self, type: str, ob: Observer) -> None:
        if type in self._observers:
            obs_of_type = self._observers[type]

            if ob not in obs_of_type:
                obs_of_type.append(ob)

    def withdraw(self, type: str, ob: Observer) -> None:
        if type in self._observers:

            if ob in self._observers[type]:
                self._observers[type].remove(ob)

    def withdrawAll(self, ob: Observer) -> None:
        for type in self._observers:
            obs = self._observers[type]

            if ob in obs:
                obs.remove(ob)

    async def notify(self, type: str, data: Any) -> None:
        if type in self._observers:
            obs = self._observers[type]

            for ob in obs:
                await ob.update(self._subject_ident, data)



# TestCases
import unittest

class ObTestCases(unittest.TestCase):
    def tes_observer(self):
        from manager.basic.observer import Subject, Observer

        event = ""
        log   = ""

        event_msg = "Doing Something..."
        log_msg   = "Logging message..."

        class S(Subject):
            EVENT = "EVENT"
            LOG   = "Log"

            def __init__(self) -> None:
                Subject.__init__(self, "S")

                self.addType(S.EVENT)
                self.addType(S.LOG)

            def do(self) -> None:
                self.notify(S.EVENT, event_msg)

            def log(self) -> None:
                self.notify(S.LOG, log_msg)

        class O(Observer):

            def __init__(self) -> None:
                Observer.__init__(self)

            def eventListen(self, data:Any) -> None:
                nonlocal event
                event = data

            def logListen(self, data:Any) -> None:
                nonlocal log
                log = data

        s = S()

        o_event = O()
        o_event.handler_install("S", o_event.eventListen)

        o_log   = O()
        o_log.handler_install("S", o_log.logListen)

        s.subscribe(S.EVENT, o_event)
        s.subscribe(S.LOG, o_log)

        s.do()
        s.log()

        self.assertEqual(event_msg, event)
        self.assertEqual(log_msg, log)
