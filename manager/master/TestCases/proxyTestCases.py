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
from manager.master.msgCell import MsgWrapper


class ProxyTestCases(unittest.IsolatedAsyncioTestCase):

    pass


class MsgWrapperTestCases(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self) -> None:
        self.msg = msg = Message("T", {})
        self.sut = MsgWrapper(msg)

    async def test_MsgWrapper_GetMsg(self) -> None:
        # Exercise and Verify
        self.assertEqual(self.msg, self.sut.get_msg())

    async def test_MsgWrapper_addConfig(self) -> None:
        key_off = "cfg_off"
        key_on = "cfg_on"

        # Exercise
        self.sut.add_config(key_on)
        self.sut.add_config_off(key_off)

        # Verify
        self.assertEqual(True, self.sut.is_turn_on(key_on))
        self.assertEqual(False, self.sut.is_turn_on(key_off))

    async def test_MsgWrapper_setConfig(self) -> None:
        # Setup
        key = "cfg"
        self.sut.add_config(key)

        # Exercise
        self.sut.set_config_on(key)
        self.assertTrue(self.sut.is_turn_on(key))

        self.sut.set_config_off(key)
        self.assertFalse(self.sut.is_turn_on(key))
