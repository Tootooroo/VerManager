from typing import *

from django.db import connections
from django.db import models
from django.utils import timezone
from django.db import connection, connections

# Create your models here.
class Revisions(models.Model):
    sn = models.CharField(max_length=50, primary_key=True) # type: ignore
    author = models.CharField(max_length=25) # type: ignore
    comment = models.CharField(max_length=2048) # type: ignore
    dateTime = models.DateTimeField(default=timezone.now) # type: ignore

    def __str__(self):
        return "%s<:>%s<:>%s" % (self.sn, self.author, self.comment)

class Versions(models.Model):
    vsn = models.CharField(max_length=50, primary_key=True) # type: ignore
    sn = models.CharField(max_length=50) # type: ignore
    dateTime = models.DateTimeField(default=timezone.now) # type: ignore

    def __str__(self):
        return self.vsn

def infoBetweenRev(rev1: str, rev2: str) -> List[str]:

    make_sure_mysql_usable()

    begin = Revisions.objects.get(pk=rev1) # type: ignore
    end = Revisions.objects.get(pk=rev2) # type: ignore

    if begin.dateTime > end.dateTime:
        tmp = begin
        begin = end
        end = tmp

    vers = Revisions.objects.filter( #type: ignore
        dateTime__gt=begin.dateTime,
        dateTime__lte=end.dateTime)

    # Mapping vers into vers's comment informations
    comments = list(map(lambda ver: ver.comment, vers))

    return comments

def make_sure_mysql_usable():
    if connection.connection and not connection.is_usable():
        del connections._connections.default
