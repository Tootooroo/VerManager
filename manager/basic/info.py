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

# info.py

import unittest
import asyncio

import typing
from yaml import load, SafeLoader
from functools import reduce

from manager.basic.mmanager import Module

M_NAME = "Info"

# Abstruction of configuration file
class Info(Module):

    def __init__(self, cfgPath: str) -> None:
        Module.__init__(self, M_NAME)

        with open(cfgPath, "r") as f:
            self._config = load(f, Loader=SafeLoader)

    async def begin(self) -> None:
        return None

    async def cleanup(self) -> None:
        return None

    def getConfig(self, *cfgKeys) -> typing.Any:
        cfgValue = self._config

        try:
            for i in cfgKeys:
                cfgValue = cfgValue[i]
        except KeyError:
            return ""

        return cfgValue

    # Value of the dict may be a string may be a dict
    def getConfigs(self) -> typing.Dict[str, typing.Any]:
        return self._config

    def validityChecking(self, predicates) -> bool:
        results = list(map(lambda p: p(self._config), predicates))
        return reduce(lambda acc, curr: acc and curr, results)

# TestCases
class InfoTestCases(unittest.TestCase):

    def setUp(self) -> None:
        # Fixture setup
        self.cfgs = Info("./config.yaml")

    def test_Info_getConfig(self) -> None:
        # Exercise
        tzvalue = self.cfgs.getConfig("TimeZone")
        prjId = self.cfgs.getConfig("Project_ID")
        cmds = self.cfgs.getConfig("BuildSet", "Builds", "GL5610", "cmd")

        # Verify
        self.assertEqual(480, tzvalue)
        self.assertEqual(34, prjId)
        self.assertEqual(
            [
                '.\\GBN\\src\\gcom_gpon_build_boot.bat 1',
                '.\\GBN\\src\\gcom_gpon_build_host.bat 1',
                'cd .\\BSP\\config\\image',
                'rar a -r 5610gpon NOBRAND_OEM_TiNetS5610_10gpon',
                'cd ..\\..\\..'
            ],
            cmds
        )

    def test_Info_getConfigs(self) -> None:
        pass

    def test_Info_validityChecking(self):
        predicates = [
            lambda c: "Address" in c,
            lambda c: "Port" in c,
            lambda c: "LogDir" in c,
            lambda c: "ResultDir" in c,
            lambda c: "GitlabUrl" in c,
            lambda c: "PrivateToken" in c,
            lambda c: "TimeZone" in c
        ]

        self.assertTrue(self.cfgs.validityChecking(predicates))
