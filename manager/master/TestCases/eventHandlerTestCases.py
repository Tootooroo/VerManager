# MIT License
#
# Copyright (c) 2020 Tootooroo
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import unittest
import asyncio
import os
import shutil

from typing import Any
from manager.basic.letter import BinaryLetter
from manager.master.eventListener import EventListener, Entry
from manager.basic.storage import Storage
from manager.master.eventHandlers \
    import binaryHandler


class EventListenerStub(EventListener):

    def __init__(self) -> None:
        EventListener.__init__(self, None)
        self._storage = Storage("./EH_STORAGE", None)

    def getModule(self, m: str) -> Any:
        return self._storage


class EventHandlerTestCases(unittest.TestCase):

    def test_EventHandler_BinaryHandler(self) -> None:
        # Setup
        with open("./TestFile", "w") as file:
            file.write("test_EventHandler_BinaryHandler")

        # Exercise
        async def testing():
            env = Entry.EntryEnv(EventListenerStub(), {})

            for lines in open("./TestFile", "r"):
                bLetter = BinaryLetter("TID", lines.encode(),
                                       parent="P", fileName="file")

                await binaryHandler(env, bLetter)
            await binaryHandler(env, BinaryLetter(
                "TID", "", parent="P", fileName="file"))

        asyncio.run(testing())

        # Verify
        self.assertTrue(os.path.exists("./EH_STORAGE/P/file"))
        with open("./EH_STORAGE/P/file") as file:
            for line in file:
                self.assertEqual(
                    "test_EventHandler_BinaryHandler",
                    line
                )

        # TearDown
        os.remove("./TestFile")
        shutil.rmtree("./EH_STORAGE")

    def test_EventHandler_LogHandler(self) -> None:
        pass

    def test_EventHandler_PostHandler(self) -> None:
        pass

    def test_EventHandler_LisAddrUpdateHandler(self) -> None:
        pass
