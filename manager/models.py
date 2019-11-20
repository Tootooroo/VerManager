from django.db import models

# Create your models here.
class Revisions(models.Model):
    sn = models.CharField(max_length=30, primary_key=True)
    author = models.CharField(max_length=25)
    comment = models.CharField(max_length=1024)

class Versions(models.Model):
    vsn = models.CharField(max_length=50)
    sn = models.CharField(max_length=30)
    author = models.CharField(max_length=25)
