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

from typing import List

from django.db import connections
from django.db import models
from django.utils import timezone
from django.db import connection


# Create your models here.
class Revisions(models.Model):
    sn = models.CharField(max_length=50, primary_key=True)
    author = models.CharField(max_length=25)
    comment = models.CharField(max_length=2048)
    dateTime = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return "%s<:>%s<:>%s" % (self.sn, self.author, self.comment)


class Versions(models.Model):
    vsn = models.CharField(max_length=50, primary_key=True)
    sn = models.CharField(max_length=50)
    dateTime = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.vsn


class Jobs(models.Model):
    jobid = models.CharField(max_length=100, primary_key=True)
    dateTime = models.DateTimeField(default=timezone.now)


def infoBetweenRev(rev1: str, rev2: str) -> List[str]:

    make_sure_mysql_usable()

    begin = Revisions.objects.get(pk=rev1)
    end = Revisions.objects.get(pk=rev2)

    if begin.dateTime > end.dateTime:
        tmp = begin
        begin = end
        end = tmp

    vers = Revisions.objects.filter(
        dateTime__gt=begin.dateTime,
        dateTime__lte=end.dateTime)

    # Mapping vers into vers's comment informations
    comments = list(map(lambda ver: ver.comment, vers))

    return comments


def make_sure_mysql_usable():
    if connection.connection and not connection.is_usable():
        del connections._connections.default
