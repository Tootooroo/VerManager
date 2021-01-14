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
from manager.master.docGen import log_content_gen, log_gen
from manager.models import Versions, Revisions
from channels.db import database_sync_to_async as db_s_2_as


class DocGenTestCases(unittest.IsolatedAsyncioTestCase):

    def setUp(self) -> None:
        # Setup
        self.v1 = Versions(vsn="v1", sn="s1")
        self.v2 = Versions(vsn="v2", sn="s3")
        self.v3 = Versions(vsn="v3", sn="s5")
        self.r1 = Revisions(sn="s1", author="author", comment="comment1")
        self.r2 = Revisions(sn="s2", author="author", comment="comment2")
        self.r3 = Revisions(sn="s3", author="author", comment="comment3")
        self.r4 = Revisions(sn="s4", author="author", comment="comment4")
        self.r5 = Revisions(sn="s5", author="author", comment="comment5")

        self.v1.save()
        self.v2.save()
        self.v3.save()
        self.r1.save()
        self.r2.save()
        self.r3.save()
        self.r4.save()
        self.r5.save()

    def tearDown(self) -> None:
        self.v1.delete()
        self.v2.delete()
        self.r1.delete()
        self.r2.delete()
        self.v3.delete()
        self.r3.delete()
        self.r4.delete()
        self.r5.delete()

    async def test_DocGen_LogContentGenerate(self) -> None:
        contents = await log_content_gen("v3")
        self.assertEqual(["comment5", "comment4"], contents)

        contents = await log_content_gen("v2")
        self.assertEqual(["comment3", "comment2"], contents)

    async def test_DocGen_LogGen(self) -> None:
        print(await log_gen("v3"))
