import manager.apps
from django.shortcuts import render
from django.template import RequestContext
from manager.misc.verControl import RevSync
from .models import Revisions

# Create your views here.
def index(request):
    return render(request, 'index.html')

def verRegPage(request):
    return render(request, 'verRegister.html')

def register(request):
    if request.method == "POST":
        try:
            revision = get_object_or_404(Revisions, pk=request.POST['verChoice'])
        except:
            return HttpResponse("Select a choice")
        else:
            # Send to dispatcher
            verSN = request.POST['Version']
            pass
    else:
        return HttpResponse("Failed")

def newRev(request):
    RevSync.revNewPush(request)
    return HttpResponse("")

def generation(request):
    pass
