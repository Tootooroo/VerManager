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
from client.messages import Message


class MessageTestCaes(unittest.IsolatedAsyncioTestCase):

    async def test_Message_toString(self) -> None:
        # Setup
        msg = Message("T1", {"C": ["1", "2"]})

        # Exercise & Verify
        self.assertEqual(Message.FORMAT_TEMPLATE %
                         ("T1", str({"C": ["1", "2"]}).replace("'", "\"")), str(msg))

    async def test_Message_fromString(self) -> None:
        # Setup
        msg_str = Message.FORMAT_TEMPLATE % ("T1", '{"C": "C1"}')

        # Exercise
        msg = Message.fromString(msg_str)

        # Verify
        self.assertEqual("T1", msg.type)
        self.assertEqual({"C": "C1"}, msg.content)

    async def test_Message_TransformCycle(self) -> None:
        # Setup
        msg = Message("T1", {"C": ["1", "2"]})
        msg_str = str(msg)

        # Exercise
        msg1 = Message.fromString(msg_str)

        # Verify
        self.assertEqual(msg.type, msg1.type)
        self.assertEqual(msg.content, msg1.content)
