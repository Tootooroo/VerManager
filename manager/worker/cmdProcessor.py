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

import typing

from typing import Callable, Coroutine
from manager.worker.processor import ProcUnit
from manager.basic.letter import Letter, CommandLetter


CommandHandler = Callable[[ProcUnit, CommandLetter], Coroutine]


class CmdProcessor(ProcUnit):

    def __init__(self, ident: str) -> None:
        ProcUnit.__init__(self, ident)
        self._hMap = {}  # type: typing.Dict[str, CommandHandler]

    async def run(self) -> None:
        pass

    async def proc(self, letter: Letter) -> None:
        if not isinstance(letter, CommandLetter):
            raise CMD_PROCESSOR_WRONG_TYPE_LETTER()

        type = letter.getType()

        await self._hMap[type](self, letter)

    async def query(self, code: int) -> None:
        pass

    async def ctrl(self, code: int) -> None:
        pass

    def cmd_proc_install(self, ident: str, handler: CommandHandler) -> None:
        if self.is_handler_exists(ident):
            return None
        self._hMap[ident] = handler

    def is_handler_exists(self, ident: str) -> bool:
        return ident in self._hMap




class CMD_PROCESSOR_WRONG_TYPE_LETTER(Exception):
    pass
