from typing import *

from django.db import models
from django.utils import timezone

# Create your models here.
class Revisions(models.Model):
    sn = models.CharField(max_length=30, primary_key=True) # type: ignore
    author = models.CharField(max_length=25) # type: ignore
    comment = models.CharField(max_length=1024) # type: ignore
    dateTime = models.DateTimeField(default=timezone.now) # type: ignore

    def __str__(self):
        return "%s<:>%s<:>%s" % (self.sn, self.author, self.comment)

class Versions(models.Model):
    vsn = models.CharField(max_length=50, primary_key=True) # type: ignore
    sn = models.CharField(max_length=30) # type: ignore
    dateTime = models.DateTimeField(default=timezone.now) # type: ignore


def infoBetweenVer(v1: str, v2, str) -> List[str]:
    ver1 = Versions.objects.get(pk=v1) # type: ignore
    ver2 = Versions.objects.get(pk=v2) # type: ignore

    begin = ver1.dateTime
    end = ver2.dateTime

    if begin > end:
        begin = ver2.dateTime
        end = ver1.dateTime

    vers = Versions.objects.filter(dateTime__gt=begin, dateTime__lt=end) # type: ignore

    # Mapping vers into vers's comment informations
    comments = list(map(lambda ver: ver.comment, vers))

    return comments
