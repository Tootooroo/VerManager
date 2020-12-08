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


import unittest
from typing import List, Optional
from client.clientEventProcessor import ClientEventProcessor
from client.messages import ClientEvent, Message


async def trivial_handler(event: ClientEvent) -> Optional[List[Message]]:
    return [Message("TEST_REPLY", {})]


class ClientEventProcessorTestCases(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self) -> None:
        self.sut = ClientEventProcessor()

    async def test_CEP_eventInstall(self) -> None:
        # Exercise
        self.sut.event_proc_install("TEST", None)

        # Verify
        self.assertTrue(self.sut.event_proc_exists("TEST"))

    async def test_CEP_eventUnisntall(self) -> None:
        # Exercise
        self.sut.event_proc_install("TEST", tirvial_handler)
        self.sut.event_proc_uninstall("TEST")

        # Verify
        self.assertFalse(self.sut.event_proc_exists("TEST"))

    async def test_CEP_eventProc(self) -> None:
        # Setup
        self.sut.event_proc_install("TEST", tirvial_handler)

        # Exercise
        self.sut.proc(ClientEvent('{"type": "TEST", "content"}'))
