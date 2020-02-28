# verRegister.py
#
# This module define a object that deal with Revisions

import manager.master.components as Components

from typing import *

from threading import Thread
from manager.models import Revisions
from django.http import HttpRequest
import re
import queue
import gitlab  # type: ignore

import json

from django.dispatch import receiver
from django.db.backends.signals import connection_created  # type: ignore

import traceback

revSyncner = None

class RevSync(Thread):
    # This queue will fill by new revision that merged into
    # repository after RevSync started and RevSync will
    # put such revision into model so the revision database
    # will remain updated
    revQueue = queue.Queue(maxsize=10) # type: queue.Queue

    def __init__(self, sInst:Any) -> None:
        Thread.__init__(self)

        self.__sInst = sInst

        cfgs = sInst.getModule('Config')
        url = cfgs.getConfig('GitlabUrl')
        token = cfgs.getConfig('PrivateToken')

        self.__project_id = cfgs.getConfig("Project_ID")

        if url == "" or token == "":
            return None
        # fixme: repo url and token key must not a constant just place these in
        #        configuration file
        self.gitlabRef = gitlab.Gitlab(url, token);
        self.gitlabRef.auth()

    def revTransfer(rev, tz):
        revision = Revisions(sn=rev.id,
                             author=rev.author_name,
                             comment=rev.message,
                             dateTime=rev.committed_date)
        try:
            revision.save()
        except:
            traceback.print_exc()

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
        pId = self.__project_id
        revisions = self.gitlabRef.projects.get(pId).commits.list(all=True)

        # Remove old datas of revisions cause these data may out of date
        # repository may be rebased so that the structure of it is very
        # different with datas in database so just remove these data and
        # load from server again
        Revisions.objects.all().delete()  # type: ignore

        # Fill revisions just retrived into model
        config = self.__sInst.getModule('Config')
        tz = config.getConfig('TimeZone')
        list(map(lambda rev: RevSync.revTransfer(rev, tz), revisions))

        return True

    @staticmethod
    def revNewPush(rev: HttpRequest) -> bool:
        RevSync.revQueue.put(rev, block=True, timeout=None)
        return True

    def gitlabWebHooksChecking(self, request: HttpRequest) -> Optional[Dict]:
        headers = request.headers  # type: ignore

        if not 'X-Gitlab-Event' in headers:
            print("X-Gitlab-Event not found")
            return None

        try:
            contentType = headers['Content-Type']
            event = headers['X-Gitlab-Event']

            if contentType == 'application/json' and event == 'Merge Request Hook':
                body = json.loads(request.body) # type: ignore
                state = body['object_attributes']['state']

                if state == 'merged':
                    return body
        except:
            return None

        return None

    # Process such a database related operation on background
    # is for the purpose of quick response to where request come
    # from. Responsbility will gain more benefit if such operation
    # to be complicated.
    def run(self):
        self.revDBInit()

        config = self.__sInst.getModule('Config')
        tz = config.getConfig('TimeZone')

        while True:
            request = RevSync.revQueue.get(block=True, timeout=None)

            # Premise of these code work correct is a merge request
            # contain only a commit if it can't be satisfied
            # should read gitlab when merge event arrived and
            # compare with database then append theses new into
            # database
            body = self.gitlabWebHooksChecking(request)

            last_commit = body['object_attributes']['last_commit']
            sn_ = last_commit['id']
            author_ = last_commit['author']['name']
            comment_ = last_commit['message']
            date_time_ = last_commit['timestamp']

            rev = Revisions(sn = sn_, author = author_, comment = comment_,
                            dateTime = date_time_)
            rev.save()

def revSyncSpawn():
    try :
        revSyncner = RevSync()

        revSyncner.revDBInit()
        revSyncner.start()
    except Exception:
        pass
