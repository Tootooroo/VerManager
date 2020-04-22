import manager.apps

import json
import time

from typing import Optional

from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.http import HttpResponseNotModified
from django.views.decorators.csrf import csrf_exempt

from functools import reduce
from django.shortcuts import render
from django.template import RequestContext
from django.shortcuts import get_object_or_404

from .master.verControl import RevSync
from .master.dispatcher import Dispatcher
from .master.worker import Task
from .basic.restricts import VERSION_MAX_LENGTH

from .basic.type import *

from datetime import datetime

import manager.master.master as S
import traceback

# Models
from .models import Revisions, Versions

# Create your views here.
def index(request):
    return render(request, 'index.html')

def verManagerPage(request):
    return render(request, 'verManager.html')

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

@csrf_exempt
def newRev(request):
    RevSync.revNewPush(request)
    return HttpResponse()

@csrf_exempt
def temporaryGen(request, revision:str):

    if S.ServerInstance is None:
        return HttpResponseBadRequest

    dispatcher = S.ServerInstance.getModule('Dispatcher')

    if dispatcher is None:
        return HttpResponseBadRequest

    # Use date as version
    version = str(datetime.now()).split(".")[0] + revision
    version = version.replace(" ", "-")

    if len(version) > VERSION_MAX_LENGTH:
        version = version[:VERSION_MAX_LENGTH]

    task = Task(version, revision, version, extra = {"Temporary":"true"})

    if task.isValid() is False:
        return HttpResponseBadRequest()

    if dispatcher.dispatch(task) == False: # type: ignore
        return HttpResponseBadRequest()

    return HttpResponse()

def generation(request):
    import os

    dispatcher = S.ServerInstance.getModule('Dispatcher')

    try:
        verIdent = request.POST['verSelect']
        dateTime = request.POST['Datetime']
        extra_info = {}

        if "logFrom" in request.POST and 'logTo' in request.POST:
            logFrom = request.POST['logFrom']
            logTo = request.POST['logTo']

            extra_info['logFrom'] = logFrom
            extra_info['logTo'] = logTo
            extra_info['datetime'] = dateTime

        version = Versions.objects.get(pk=verIdent)

        if version == None:
            return HttpResponseBadRequest()

        task = Task(verIdent, version.sn, verIdent, extra = extra_info)
        if task.isValid() is False:
            return HttpResponseBadRequest()

        if dispatcher.dispatch(task) == False:
            return HttpResponseBadRequest()

    except:
        traceback.print_exc()
        return HttpResponseBadRequest()

    return HttpResponse()

def isGenerationDone(request):
    dispatcher = S.ServerInstance.getModule('Dispatcher')

    verIdent = request.POST['verSelect']

    if not dispatcher.isTaskExists(verIdent):
        return HttpResponseBadRequest()

    if dispatcher.isTaskFinished(verIdent):
        resultUrl = dispatcher.retrive(verIdent)
        return HttpResponse(resultUrl)
    elif dispatcher.isTaskInProc(verIdent) or dispatcher.isTaskPrepare(verIdent):

        # Update last counter of Task. This counter will
        # give help to remove outdated tasks
        dispatcher.taskLastUpdate(verIdent)

        return HttpResponseNotModified()
    elif dispatcher.isTaskFailure(verIdent):
        dispatcher.removeTask(verIdent)
        return HttpResponseBadRequest()

    # Task is failure or the task is not exists
    return HttpResponseBadRequest()

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

def versionRetrive(request):
    vers = Versions.objects.all()
    vers = vers.order_by('-dateTime')

    if len(vers) == 0:
        return HttpResponseNotModified()

    verStr = reduce(lambda acc,ver: str(acc) + "__<?>__" + str(ver), vers)
    return HttpResponse(verStr)
