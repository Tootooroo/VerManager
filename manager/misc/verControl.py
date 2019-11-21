# verRegister.py
#
# This module define a object that deal with Revisions

import typing

from threading import Thread
from manager.models import Revisions
from django.http import HttpRequest
import re
import queue
import gitlab

from django.dispatch import receiver
from django.db.backends.signals import connection_created

class RevSync(Thread):

    # This queue will fill by new revision that merged into
    # repository after RevSync started and RevSync will
    # put such revision into model so the revision database
    # will remain updated
    revQueue = queue.Queue(maxsize=10)
    count = 0

    def __init__(self):
        Thread.__init__(self)

    def revTransfer(rev):
        revision = Revisions(sn=rev.id,
                             author=rev.author_name,
                             comment=rev.message,
                             dateTime=RevSync.timeFormat(rev.committed_date, "+08:00"))
        revision.save()
        return revision

    # format of offset if "+08:00"
    def timeFormat(timeStr: typing.AnyStr, offset: typing.AnyStr) -> typing.AnyStr:
        pattern = "([0-9]*-[0-9]*-[0-9]*T[0-9]*:[0-9]*:[0-9]*)"

        m = re.search(pattern, timeStr)
        if m == None:
            return ""

        formatDate = m.group()
        return formatDate + offset

    @receiver(connection_created)
    def revDBInit(sender, **kwargs) -> bool:
        # fixme: repo url and token key must not a constant place these in
        #        configuration file
        gl = gitlab.Gitlab("http://gpon.git.com:8011", "4mU2joxotSkzTqLPhvgu");
        gl.auth()

        revisions = gl.projects.get(34).commits.list()

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

    def httpReq2Rev(self, req: HttpRequest) -> Revisions:
        pass

    # Process such a database related operation on background
    # is for the purpose of quick response to where request come
    # from. Responsbility will gain more benefit if such operation
    # to be complicated.
    def run(self):
        request = RevSync.revQueue.get(block=True, timeout=None)
        rev = self.httpReq2Rev(request)
        rev.save()
