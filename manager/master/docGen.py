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


import os
import typing as T
from manager.models import Versions, Revisions
from channels.db import database_sync_to_async as db_s_2_as


async def default_content_gen(rev: Revisions) -> str:
    return rev.comment


async def log_gen(version: str) -> T.Optional[str]:
    pass



async def log_content_gen(version: str) -> T.List[str]:

    if os.path.exists("custom.py"):
        from custom.py import log_generate
        trans = log_generate
    else:
        trans = default_content_gen

    revs = changes(version)
    content = []  # type: T.List[str]
    for rev in revs:
        content.append(await trans(rev))

    return content


async def changes(version: str) -> T.List[Revisions]:
    """
    Return revs that a version have.
    """

    target_version = Versions.objects.get(vsn=version)

    vers = await db_s_2_as(Versions.objects.filter)(
        dateTIme__lte=target_version.dateTime
    )

    revs = []  # type: T.List[Revisions]
    for ver in vers:
        rev = db_s_2_as(Revisions.objects.get)(ver.sn)
        revs.append(rev)

    return revs
