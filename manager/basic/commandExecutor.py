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

import asyncio
import tempfile
from datetime import datetime
import subprocess
from manager.basic.util import packShellCommands, execute_shell
from typing import List, Optional, IO


class CommandExecutor:

    def __init__(self, cmds: List[str] = None) -> None:
        self._cmds = cmds  # type: Optional[List[str]]
        self._max_stucked_time = 3600
        self._running = False
        self._last_stucked = None  # type: Optional[datetime]
        self._last_pos = 0
        self._ret = 0
        self._ref = None  # type: Optional[subprocess.Popen]

    def _reset(self) -> None:
        self._running = False
        self._last_pos = 0
        self._last_stucked = None

    def stop(self) -> None:
        if self._ref is not None:
            self._ref.terminate()
            self._reset()

    async def run(self) -> int:

        if self._cmds is None:
            return -1

        command_str = packShellCommands(self._cmds)
        output = tempfile.TemporaryFile("w")

        self._running = True

        ref = execute_shell(command_str, stdout=output, stderr=output)
        if ref is None:
            self._ret = -1
            self._reset()
            return -1
        else:
            self._ref = ref

        while True:
            # Check whether the command done
            ret = ref.poll()
            if ret is not None:
                self._ret = ret
                break

            # Check whether the command is stucked
            if self.isStucked(output):
                self._ret = -1
                ref.terminate()
                break

            await asyncio.sleep(1)

        self._ref = None
        self._running = False

        if ret is None:
            return -1

        self._reset()
        return ret

    def return_code(self) -> int:
        return self._ret

    def isRunning(self) -> bool:
        return self._running

    def isStucked(self, output: IO[str]) -> bool:
        current_pos = output.tell()

        # Stucked from last position
        if current_pos == self._last_pos:
            current = datetime.utcnow()
            if self._last_stucked is None:
                self._last_stucked = datetime.utcnow()
            else:
                # Stucked timeout
                return (current - self._last_stucked).seconds > \
                    self._max_stucked_time
        else:
            if self._last_stucked is not None:
                self._last_stucked = None
            self._last_pos = current_pos

        return False

    def getStuckedLimit(self) -> int:
        return self._max_stucked_time

    def setStuckedLimit(self, limit: int) -> None:
        self._max_stucked_time = limit

    def setCommand(self, cmds: List[str]) -> None:
        self._cmds = cmds
