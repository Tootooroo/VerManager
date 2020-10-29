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

import abc
from typing import Optional, Dict
from manager.basic.letter import NotifyLetter

WORKER_STATE_CHANGED = "WSC"


class Notify(abc.ABC):

    def __init__(self, ident: str, type: str,
                 content: Dict) -> None:
        self.who = ident
        self.type = type
        self.content = content

    @staticmethod
    def transform(nl: NotifyLetter) -> Optional['Notify']:
        type = nl.notifyType()

        # type must in this Dict
        assert(type in FROM_LETTER_TO_NOTIFY)

        return FROM_LETTER_TO_NOTIFY[type](nl)

    @abc.abstractstaticmethod
    def fromLetter(nl: NotifyLetter) -> Optional['Notify']:
        """
        Generate Notify from NotifyLetter
        """

    @abc.abstractmethod
    def toLetter(self) -> NotifyLetter:
        """
        Generate NotifyLetter from Notify
        """


class WSCNotify(Notify):

    ONLINE = "0"
    WAITING = "1"
    OFFLINE = "2"
    DIRTY = "3"
    CLEAN = "4"

    def __init__(self, ident: str, state: str) -> None:
        Notify.__init__(
            self, ident, WORKER_STATE_CHANGED, {'state': state})

    def fromWho(self) -> str:
        return self.who

    def state(self) -> str:
        return self.content['state']

    @staticmethod
    def fromLetter(nl: NotifyLetter) -> Optional['WSCNotify']:
        content = nl.notifyContent()
        if 'state' not in content:
            return None
        return WSCNotify(nl.notifyFrom(), content['state'])

    def toLetter(self) -> NotifyLetter:
        return NotifyLetter(self.who, self.type, self.content)


# Dict that contain fromLetters
FROM_LETTER_TO_NOTIFY = {
    WORKER_STATE_CHANGED: WSCNotify.fromLetter
}
