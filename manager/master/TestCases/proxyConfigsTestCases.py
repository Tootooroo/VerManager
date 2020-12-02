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
import typing as T
from manager.master.proxy_configs import ProxyConfigs
from manager.master.exceptions import BASIC_CONFIG_IS_COVERED
from client.messages import Message

def handle(msg: Message, who: T.List[str], val: str) -> None:
    return None


def handle1(msg: Message, who: T.List[str], val: str) -> None:
    who.append(val)


class ProxyConfigsTestCases(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self) -> None:
        self.sut = ProxyConfigs()

    async def test_ProxyConfigs_AddConfig(self) -> None:
        # Exercise
        self.sut.add_config("cfg", handle, ["ON", "OFF"])

        # Verify
        self.assertEqual((handle, ["ON", "OFF"]), self.sut.get_config("cfg"))

    async def test_proxyConfigs_AddInvalidConfig(self) -> None:
        """
        Desc: Add a config to cover the special config
        Expect: The Add op should not success.
        """
        try:
            self.sut.add_config("is_broadcast", handle, ["ON", "OFF"])
            # Should not success.
            self.assertTrue(False)
        except BASIC_CONFIG_IS_COVERED:
            pass

    async def test_ProxyConfigs_RemoveConfig(self) -> None:
        """
        Desc: Remove a non-basic config from ProxyConfigs.
        """
        self.sut.add_config("cfg", handle, ["ON", "OFF"])

        # Exercise
        self.sut.rm_config("cfg")

        # Verify
        self.assertFalse(self.sut.is_exists("cfg"))

    async def test_ProxyConfigs_ApplyConfig(self) -> None:
        """
        Desc: Apply configs to a message.
        """
        # Setup
        msg = Message("T", {})
        self.sut.add_config("CFG_APPLY", handle1, ["CLI1", "CLI2"])

        # Exercise
        msg, who = self.sut.apply({"CFG_APPLY": "CLI1"}, msg)

        # Verify
        self.assertEqual(["CLI1"], who)

    async def test_ProxyConfigs_ApplyWrongValue(self) -> None:
        """
        Desc: Apply wrong value to config.
        """
        # Setup
        msg = Message("T", {})
        self.sut.add_config("CFG_WRONG", handle1, ["CLI1", "CLI2"])

        # Exercise
        msg, who = self.sut.apply({"CFG_WRONG": "CLI3"}, msg)

        # Verify
        self.assertEqual([], who)
