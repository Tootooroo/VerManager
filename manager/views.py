import manager.apps
from django.shortcuts import render
from django.template import RequestContext

# Create your views here.
def index(request):
    return render(request, 'index.html')

def verRegPage(request):
    return render(request, 'verRegister.html')

def register(request):
    return render(request, 'register.html')
