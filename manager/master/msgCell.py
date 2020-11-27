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
from typing import Optional
from client.messages import Message


class MsgSource(abc.ABC):

    def __init__(self, src_id: str) -> None:
        self.src_id = src_id

    @abc.abstractmethod
    async def sendMsg(self, msg: Message) -> None:
        """ Send Message """

    @abc.abstractmethod
    async def gen_msg(self) -> Optional[Message]:
        """ Generate Message """


class MsgUnit:

    def __init__(self, msg_type: str, source: MsgSource) -> None:
        self._type = msg_type
        self._source = source

    def src_id(self) -> str:
        return self._source.src_id

    def msg_type(self) -> str:
        return self._type

    async def gen_msg(self) -> Optional[Message]:
        return await self._source.gen_msg()
