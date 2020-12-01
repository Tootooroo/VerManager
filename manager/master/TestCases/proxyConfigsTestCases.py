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
from manager.master.proxy_configs import ProxyConfigs
from manager.master.exceptions import BASIC_CONFIG_IS_COVERED


class ProxyConfigsTestCases(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self) -> None:
        self.sut = ProxyConfigs()

    async def test_ProxyConfigs_AddConfig(self) -> None:
        # Exercise
        self.sut.add_config("cfg", None)

        # Verify
        self.assertIsNone(self.sut.get_config("cfg"))

    async def test_proxyConfigs_AddInvalidConfig(self) -> None:
        """
        Desc: Add a config to cover the special config
        Expect: The Add op should not success.
        """
        try:
            self.sut.add_config("is_broadcast", None)
            # Should not success.
            self.assertTrue(False)
        except BASIC_CONFIG_IS_COVERED:
            pass

    async def test_ProxyConfigs_RemoveConfig(self) -> None:
        pass
