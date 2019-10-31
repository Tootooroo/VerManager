from django.shortcuts import render

# Create your views here.
def index(request):
    return render(request, 'index.html')

def oemReg(request):
    return render(request, 'index.html')
