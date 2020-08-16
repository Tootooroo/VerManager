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

# receiver.py

from ..basic.mmanager import ModuleDaemon
from .server import Server
from ..basic.observer import Subject


M_NAME = "Recevier"


class Receiver(Subject, ModuleDaemon):

    def __init__(self, server: Server) -> None:
        # Init as a ModuleDaemon
        ModuleDaemon.__init__(self, M_NAME)

        # Init as a Subject
        Subject.__init__(self, M_NAME)
        self.addType("Letter")

        self._server = server
        self._stop = False

    async def stop(self) -> None:
        self._stop = True

    def needStop(self) -> bool:
        return self._stop

    def status(self) -> int:
        return self._stop

    async def run(self) -> None:
        server = self._server

        while True:
            if self._stop == 1:
                return None

            try:
                letter = await server.waitLetter()

                # notify to registered
                self.notify("Letter", letter)

            except (ConnectionError, BrokenPipeError, ConnectionResetError):
                # Connection between server
                # is not maintained by Receiver
                continue
