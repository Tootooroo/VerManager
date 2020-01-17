# verRegister.py
#
# This module define a object that deal with Revisions

from typing import *

from threading import Thread
from manager.models import Revisions
from django.http import HttpRequest
import re
import queue
import gitlab

import json

from django.dispatch import receiver
from django.db.backends.signals import connection_created

import traceback

revSyncner = None

class RevSync(Thread):
    # This queue will fill by new revision that merged into
    # repository after RevSync started and RevSync will
    # put such revision into model so the revision database
    # will remain updated
    revQueue = queue.Queue(maxsize=10) # type: queue.Queue

    def __init__(self):
        Thread.__init__(self)

        # fixme: repo url and token key must not a constant just place these in
        #        configuration file
        self.gitlabRef = gitlab.Gitlab("http://gpon.git.com:8011", "4mU2joxotSkzTqLPhvgu");
        self.gitlabRef.auth()

    def revTransfer(rev):
        revision = Revisions(sn=rev.id,
                             author=rev.author_name,
                             comment=rev.message,
                             dateTime=RevSync.timeFormat(rev.committed_date, "+08:00"))
        try:
            revision.save()
        except:
            traceback.print_exc()

        return revision

    # format of offset if "+08:00"
    @staticmethod
    def timeFormat(timeStr: str, offset: str) -> str:
        pattern = "([0-9]*-[0-9]*-[0-9]*T[0-9]*:[0-9]*:[0-9]*)"

        m = re.search(pattern, timeStr)
        if m is None:
            return ""

        formatDate = m.group()
        return formatDate + offset

    def revDBInit(self) -> bool:
        revisions = self.gitlabRef.projects.get(34).commits.list(all=True)

        # Remove old datas of revisions cause these data may out of date
        # repository may be rebased so that the structure of it is very
        # different with datas in database so just remove these data and
        # load from server again
        Revisions.objects.all().delete()

        # Fill revisions just retrived into model
        list(map(RevSync.revTransfer, revisions))

        return True

    def revNewPush(rev: HttpRequest) -> bool:
        RevSync.revQueue.put(rev, block=True, timeout=None)
        return True

    def gitlabWebHooksChecking(self, request: HttpRequest) -> Optional[Dict]:
        headers = request.headers

        if not 'X-Gitlab-Event' in headers:
            print("X-Gitlab-Event not found")
            return None

        try:
            contentType = headers['Content-Type']
            event = headers['X-Gitlab-Event']

            if contentType == 'application/json' and event == 'Merge Request Hook':
                body = json.loads(request.body)
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
        while True:
            request = RevSync.revQueue.get(block=True, timeout=None)

            # Premise of these code work correct is a merge request
            # contain only a commit if it can't be satisfied
            # should read gitlab when merge event arrived and
            # compare with database then append theses new into
            # database
            body = self.gitlabWebHooksChecking(request)

            if body == None:
                continue

            last_commit = body['object_attributes']['last_commit']
            sn_ = last_commit['id']
            author_ = last_commit['author']['name']
            comment_ = last_commit['message']
            date_time_ = RevSync.timeFormat(last_commit['timestamp'], '+08:00')

            rev = Revisions(sn = sn_,
                            author = author_,
                            comment = comment_,
                            dateTime = date_time_)
            rev.save()

def revSyncSpawn(sender, **kwargs):
    try :
        revSyncner = RevSync()

        revSyncner.revDBInit()
        revSyncner.start()
    except Exception:
        pass
