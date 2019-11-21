from django.db import models
from django.utils import timezone

# Create your models here.
class Revisions(models.Model):
    sn = models.CharField(max_length=30, primary_key=True)
    author = models.CharField(max_length=25)
    comment = models.CharField(max_length=1024)
    dateTime = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return "%s<:>%s<:>%s" % (self.sn, self.author, self.comment)

class Versions(models.Model):
    vsn = models.CharField(max_length=50)
    sn = models.CharField(max_length=30)
    author = models.CharField(max_length=25)
    dateTime = models.DateTimeField(default=timezone.now)
