import manager.apps

import json

from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.http import HttpResponseNotModified

from functools import reduce
from django.shortcuts import render
from django.template import RequestContext

from .misc.verControl import RevSync

# Models
from .models import Revisions, Versions

# Create your views here.
def index(request):
    return render(request, 'index.html')

def verRegPage(request):
    return render(request, 'verRegister.html')

def register(request):
    try:
        verName = request.POST['Version']
        revision = request.POST['verChoice']

        # Already registered respons with 304(Not modified)
        if len(Versions.objects.filter(vsn=verName)) != 0:
            return HttpResponseNotModified()

        newVer = Versions(vsn = verName, sn = revision)
        newVer.save()

        return HttpResponse()

    except:
        return HttpResponseBadRequest()

    return HttpResponseNotModified()

def newRev(request):
    RevSync.revNewPush(request)
    return HttpResponse()

# request: {Version: 'ver_name'}
def generation(request):
    pass

def revisionRetrive(request):
    beginRev = None
    numOfRev = None

    info = json.loads(request.body.decode('utf8'))

    if request.method == "POST":
        if 'beginRev' in info and 'numOfRev' in info:
            beginRev = info['beginRev']
            numOfRev = info['numOfRev']

        # Search for 'numOfRev' lasted revisions
        numOfRev_int = int(numOfRev)

        if beginRev == "null":
            # Retrive revisions from the laster revision
            revs = Revisions.objects.all()
        else:
            # Retrive revisions before the specified revision
            theRev = Revisions.objects.get(pk=beginRev)
            revs = Revisions.objects.filter(dateTime__lt=theRev.dateTime)

        revs = revs.order_by('-dateTime')
        revs = revs[0:min(numOfRev_int, len(revs))]

        if len(revs) == 0:
            return HttpResponseNotModified()

        revStr = reduce(lambda acc,rev: str(acc) + "__<?>__" + str(rev), revs)
        return HttpResponse(revStr)

    # Request does not contain info is need
    # to retrive revisions
    return HttpResponseBadRequest()
