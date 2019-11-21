import manager.apps

import json

from functools import reduce
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.shortcuts import render
from django.template import RequestContext
from .models import Revisions

# Create your views here.
def index(request):
    return render(request, 'index.html')

def verRegPage(request):
    return render(request, 'verRegister.html')

def register(request):
    pass

def newRev(request):
    RevSync.revNewPush(request)
    return HttpResponse("")

def generation(request):
    pass

def revisionRetrive(request):
    info = json.loads(request.body.decode('utf8'))

    if request.method == "POST":
        try:
            beginRev = info['beginRev']
            numOfRev = info['numOfRev']
        except:
            # Request does not contain info is need
            # to retrive revisions
            return HttpResponseBadRequest()
        else:
            # Search for 'numOfRev' lasted revisions
            numOfRev_int = int(numOfRev)

            if beginRev == "null":
                # Retrive revisions from the laster revision
                revs = Revisions.objects.all().order_by('-dateTime')[0:numOfRev_int]
            else:
                # Retrive revisions before the specified revision
                theRev = Revisions.objects.get(pk=beginRev)
                revs = Revisions.objects.filter(dateTime__lte=theRev.dateTime).order_by('-dateTime')[0:numOfRev_int]

            revStr = reduce(lambda acc,rev: str(acc) + "__<?>__" + str(rev), revs)

            return HttpResponse(revStr)
