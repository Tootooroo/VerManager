from typing import *

from django.db import models
from django.utils import timezone

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

def infoBetweenVer(v1: str, v2: str) -> List[str]:
    ver1 = Versions.objects.get(pk=v1) # type: ignore
    ver2 = Versions.objects.get(pk=v2) # type: ignore

    begin = rev1 = Revisions.objects.get(pk=ver1.sn) # type: ignore
    end = rev2 = Revisions.objects.get(pk=ver2.sn) # type: ignore

    if begin.dateTime > end.dateTime:
        begin = rev2
        end = rev1

    vers = Revisions.objects.filter(
        dateTime__gt=begin.dateTime,
        dateTime__lte=end.dateTime) # type: ignore

    # Mapping vers into vers's comment informations
    comments = list(map(lambda ver: ver.comment, vers))

    return comments
