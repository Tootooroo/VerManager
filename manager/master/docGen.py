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
from texttable import Texttable


__all__ = ["log_gen"]


async def log_gen(version: str, path: str = "./log.txt") -> T.Optional[str]:
    target_version = await db_s_2_as(Versions.objects.get)(vsn=version)

    vers = await db_s_2_as(Versions.objects.filter)(
        dateTime__lte=target_version.dateTime
    )

    vers = vers.order_by('-dateTime')

    ver_contents = []  # type: T.List[T.List[str]]
    vers_list = await db_s_2_as(list)(vers)

    for ver in vers_list:
        ver_contents.append(
            await log_content_gen(ver.vsn)
        )

    if os.path.exists("custom.py"):
        from custom import doc_gen
        try:
            await doc_gen(ver_contents, path)
        except Exception:
            return None
    else:
        changelogfile = open(path, "w")
        # Default Action
        for content in ver_contents:
            [changelogfile.write(line+"\n") for line in content]

    return path


async def log_content_gen(version: str) -> T.List[str]:

    revs = await changes(version)
    content = [version]  # type: T.List[str]
    for rev in revs:
        content.append(rev.comment)

    return content


async def changes(version: str) -> T.List[Revisions]:
    """
    Return revs that a version have.
    """

    target_version = await db_s_2_as(Versions.objects.get)(vsn=version)

    vers = await db_s_2_as(Versions.objects.filter)(
        dateTime__lte=target_version.dateTime
    )
    # In descending order
    vers = vers.order_by('-dateTime')

    vers_list = await db_s_2_as(list)(vers)
    length = len(vers_list)
    if length < 2:
        return []
    else:
        return await range_of_revs(vers_list[0].vsn, vers_list[1].vsn)


async def range_of_revs(vsn1: str, vsn2: str) -> T.List[Revisions]:
    ver1 = await db_s_2_as(Versions.objects.get)(vsn=vsn1)
    ver2 = await db_s_2_as(Versions.objects.get)(vsn=vsn2)

    begin_rev = await db_s_2_as(Revisions.objects.get)(sn=ver1.sn)
    end_rev = await db_s_2_as(Revisions.objects.get)(sn=ver2.sn)

    if begin_rev.dateTime > end_rev.dateTime:
        tmp = begin_rev
        begin_rev = end_rev
        end_rev = tmp

    revs = await db_s_2_as(Revisions.objects.filter)(
        dateTime__gt=begin_rev.dateTime,
        dateTime__lte=end_rev.dateTime
    )
    revs = revs.order_by("-dateTime")

    return await db_s_2_as(list)(revs)
