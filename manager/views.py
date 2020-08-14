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


from typing import cast
from django.http import HttpResponse, HttpResponseBadRequest
from django.http import HttpResponseNotModified
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from django.shortcuts import render
from .master.verControl import RevSync
from .master.dispatcher import Dispatcher
from .master.worker import Task
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from .serializers import VersionSerializer, RevisionSerializer, \
    BuildInfoSerializer, VersionInfoSerializer

import manager.master.master as S

# Models
from .models import Revisions, Versions


# Create your views here.
class VersionViewSet(viewsets.ModelViewSet):
    queryset = Versions.objects.all()
    serializer_class = VersionSerializer

    @action(detail=False, methods=['post'])
    def register(self, request) -> Response:
        try:
            serializer = VersionInfoSerializer(data=request.data)

            if not serializer.is_valid():
                return HttpResponseBadRequest()

            vers = Versions.objects.filter(vsn=serializer.data['vsn'])
            if list(vers) == []:
                newVer = Versions(vsn=serializer.data['vsn'],
                                  sn=serializer.data['sn'])
                newVer.save()
            else:
                return HttpResponseBadRequest("exists")

        except IndexError:
            return HttpResponseBadRequest("indexError")

        serilizer = self.get_serializer(newVer)
        return Response(serilizer.date)

    @action(detail=False, methods=['put'])
    def ver_update(self, request) -> Response:
        try:
            serializer_data = VersionInfoSerializer(data=request.data)

            if not serializer_data.is_valid():
                return HttpResponseBadRequest()

            ver = Versions.objects.get(vsn__exact=serializer_data.data['vsn'])
            ver.sn = serializer_data.data['sn']
            ver.save()

        except ObjectDoesNotExist:
            return HttpResponseBadRequest("Version does not exist.")

        return Response()

    @action(detail=True, methods=['delete'])
    def delete(self, request, pk=None) -> Response:
        try:
            theVersion = Versions.objects.get(pk=pk)
            theVersion.delete()
        except ObjectDoesNotExist:
            return HttpResponseBadRequest()

        return Response()

    @action(detail=True, methods=['put'])
    def generate(self, request, pk=None) -> Response:

        if len(request.data) == 0:
            extra = {}
        else:
            generate_info = BuildInfoSerializer(data=request.data)
            if not generate_info.is_valid():
                return HttpResponseBadRequest("Generate info is not valid")

            extra = generate_info.data

        try:
            version = Versions.objects.get(pk=pk)
        except ObjectDoesNotExist:
            return HttpResponseBadRequest("Version does not exists.")

        print(extra)
        task = Task(pk, version.sn, pk, extra=extra)
        if task.isValid() is False:
            return HttpResponseBadRequest()

        assert(S.ServerInstance is not None)
        dispatcher = cast(Dispatcher, S.ServerInstance.getModule('Dispatcher'))

        if dispatcher.dispatch(task) is False:
            return HttpResponseBadRequest()

        return Response('Success')

    @csrf_exempt
    @action(detail=True, methods=['put'])
    def temporaryGen(self, request, pk=None) -> Response:

        assert(S.ServerInstance is not None)
        dispatcher = cast(Dispatcher, S.ServerInstance.getModule('Dispatcher'))

        revision = pk

        version = str(timezone.localtime())
        version = version.split(".")[0].replace("-", "").\
            replace(":", "").replace(" ", "") + "_" + revision[0:10]

        task = Task(version, revision, version,
                    extra = {"Temporary":"true"})

        if not task.isValid():
            return HttpResponseBadRequest()

        if dispatcher.dispatch(task) == False:
            return HttpResponseBadRequest()

        return HttpResponse()


    @action(detail=True, methods=['post'])
    def gen_status_query(self, request, pk=None) -> Response:
        assert(S.ServerInstance is not None)
        dispatcher = cast(Dispatcher, S.ServerInstance.getModule('Dispatcher'))

        if not dispatcher.isTaskExists(pk):
            return HttpResponseBadRequest("Not Exists")

        if dispatcher.isTaskFinished(pk):
            resultUrl = dispatcher.retrive(pk)
            return Response(resultUrl)

        elif dispatcher.isTaskInProc(pk) or dispatcher.isTaskPrepare(pk):

            # Update last counter of Task. This counter will
            # give help to remove outdated tasks
            dispatcher.taskLastUpdate(pk)
            return HttpResponseNotModified()

        elif dispatcher.isTaskFailure(pk):
            dispatcher.removeTask(pk)
            return HttpResponseBadRequest()

        return HttpResponseBadRequest()


class RevisionViewSet(viewsets.ModelViewSet):
    queryset = Revisions.objects.all().order_by('-dateTime')
    serializer_class = RevisionSerializer

    @action(detail=True, methods=['get'])
    def getSomeRevsFrom(self, request, pk=None) -> Response:
        try:
            num = int(request.query_params['num'])
            if num == 0:
                return HttpResponseNotModified()
        except (ValueError, KeyError):
            return HttpResponseBadRequest()

        beginRev = self.get_object()
        revs = Revisions.objects.order_by('-dateTime').\
            filter(dateTime__lt=beginRev.dateTime)
        revs.order_by('-dateTime')

        serilizer = self.get_serializer(revs[:num], many=True)
        return Response(serilizer.data)

    @action(detail=False, methods=['get'])
    def getSomeRevs(self, request) -> Response:
        try:
            num = int(request.query_params['num'])
            if num == 0:
                return HttpResponseNotModified()
        except (ValueError, KeyError):
            return HttpResponseBadRequest()

        revs = Revisions.objects.all().order_by('-dateTime')
        serializer = self.get_serializer(revs[:num], many=True)

        return Response(serializer.data)


def index(request):
    return render(request, 'index.html')


def verManagerPage(request):
    return render(request, 'verManager.html')


@csrf_exempt
def newRev(request):
    RevSync.revNewPush(request)
    return HttpResponse()
