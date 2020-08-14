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

# verRegister.py
#
# This module define a object that deal with Revisions

import unittest
import django.db.utils
from typing import Any, Optional, Dict

from manager.basic.type import State, Ok, Error
from manager.basic.util import map_strict
from manager.basic.mmanager import ModuleDaemon
from manager.models import Revisions, make_sure_mysql_usable
from django.http import HttpRequest
import re
import queue
import gitlab  # type: ignore

import json

from manager.basic.info import M_NAME as INFO_M_NAME

revSyncner = None
M_NAME = "RevSyncner"


class RevSync(ModuleDaemon):

    # This queue will fill by new revision that merged into
    # repository after RevSync started and RevSync will
    # put such revision into model so the revision database
    # will remain updated
    revQueue = queue.Queue(maxsize=10)  # type: queue.Queue

    def __init__(self, sInst: Any) -> None:
        global M_NAME

        ModuleDaemon.__init__(self, M_NAME)

        self._stop = False

        self._sInst = sInst

    async def begin(self) -> None:
        return None

    async def cleanup(self) -> None:
        return None

    async def stop(self) -> None:
        self._stop = True

    def needStop(self) -> bool:
        return self._stop

    def connectToGitlab(self) -> State:
        cfgs = self._sInst.getModule(INFO_M_NAME)
        url = cfgs.getConfig('GitlabUrl')
        token = cfgs.getConfig('PrivateToken')

        self._project_id = cfgs.getConfig("Project_ID")

        if url == "" or token == "":
            return Error
        # fixme: repo url and token key must not a constant just place these in
        #        configuration file
        self.gitlabRef = gitlab.Gitlab(url, token)

        try:
            self.gitlabRef.auth()
        except Exception:
            return Error

        return Ok

    def revTransfer(rev, tz):
        revision = Revisions(sn=rev.id,
                             author=rev.author_name,
                             comment=rev.message,
                             dateTime=rev.committed_date)
        try:
            revision.save()
        except Exception:
            pass

        return revision

    # format of offset if "+08:00"
    @staticmethod
    def timeFormat(timeStr: str, offset: str) -> str:
        return timeStr
        print(timeStr)
        pattern = "([0-9]*-[0-9]*-[0-9]*T[0-9]*:[0-9]*:[0-9]*)"

        m = re.search(pattern, timeStr)
        if m is None:
            return ""

        formatDate = m.group()
        formatDate = formatDate.replace("T", " ")
        return formatDate + offset

    def revDBInit(self) -> bool:
        pId = self._project_id
        revisions = self.gitlabRef.projects.get(pId).commits.list(all=True)

        # Remove old datas of revisions cause these data may out of date
        # repository may be rebased so that the structure of it is very
        # different with datas in database so just remove these data and
        # load from server again
        try:
            Revisions.objects.all().delete()  # type: ignore

            # Fill revisions just retrived into model
            config = self._sInst.getModule(INFO_M_NAME)
            tz = config.getConfig('TimeZone')

            map_strict(lambda rev: RevSync.revTransfer(rev, tz), revisions)

        except django.db.utils.ProgrammingError:
            return False
        except Exception:
            pass

        return True

    @staticmethod
    def revNewPush(rev: HttpRequest) -> bool:
        RevSync.revQueue.put(rev, block=True, timeout=None)
        return True

    def gitlabWebHooksChecking(self, request: HttpRequest) -> Optional[Dict]:
        headers = request.headers  # type: ignore

        if 'X-Gitlab-Event' not in headers:
            print("X-Gitlab-Event not found")
            return None

        try:
            contentType = headers['Content-Type']
            event = headers['X-Gitlab-Event']

            if contentType == 'application/json' \
               and event == 'Merge Request Hook':

                body = json.loads(request.body)  # type: ignore
                state = body['object_attributes']['state']

                if state == 'merged':
                    return body
        except Exception:
            return None

        return None

    def _requestHandle(self, request: HttpRequest) -> bool:
        # Premise of these code work correct is a merge request
        # contain only a commit if it can't be satisfied
        # should read gitlab when merge event arrived and
        # compare with database then append theses new into
        # database
        body = body = self.gitlabWebHooksChecking(request)

        if body is None:
            return False

        last_commit = body['object_attributes']['last_commit']
        sn_ = last_commit['id']
        author_ = last_commit['author']['name']
        comment_ = last_commit['message']
        date_time_ = last_commit['timestamp']

        make_sure_mysql_usable()

        rev = Revisions(sn=sn_, author=author_, comment=comment_,
                        dateTime=date_time_)
        rev.save()

        return True

    # Process such a database related operation on background
    # is for the purpose of quick response to where request come
    # from. Responsbility will gain more benefit if such operation
    # to be complicated.
    async def run(self) -> None:

        if self.connectToGitlab() is Error:
            return None

        if self.revDBInit() is False:
            return None

        while True:

            if self._stop is True:
                return None

            request = RevSync.revQueue.get(block=True, timeout=None)

            self._requestHandle(request)


# TestCases
class HttpRequest_:

    def __init__(self):
        self.headers = ""
        self.body = ""


class VerControlTestCases(unittest.TestCase):

    def test_new_rev(self):
        import time
        from manager.models import Revisions

        revSyncer = RevSync(None)

        request = HttpRequest_()
        request.headers = {'Content-Type': 'application/json',
                           'X-Gitlab-Event': 'Merge Request Hook'}

        request.body = '{ "object_attributes": {\
                            "state": "merged",\
                            "last_commit": {\
                              "id": "12345678",\
                              "message": "message",\
                              "timestamp": "2019-05-09T01:39:08Z",\
                              "author": {\
                                "name": "root"\
                              }\
                            }\
                           }\
                         }'

        revSyncer._requestHandle(request)

        time.sleep(0.5)

        rev = Revisions.objects.get(pk='12345678')

        self.assertEqual("12345678", rev.sn)
        self.assertEqual("message", rev.comment)
        self.assertEqual("root", rev.author)
        self.assertEqual("2019-05-09 01:39:08+00:00", str(rev.dateTime))
