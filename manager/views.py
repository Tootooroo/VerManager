from django.shortcuts import render

from .form import UploadedFileForm
from .misc.oemRegister import oemRegister

# Create your views here.
def index(request):
    return render(request, 'index.html')

def oemDoRegister(request) -> bool:
    if request.method == 'POST':
        form = UploadedFileForm(request.POST, request.FILES)
        if form.is_valid():
            isRegisterSuccess = oemRegister(form.cleaned_data['version'],
                                            request.FILES['file'])
        else:
            return False
    return isRegisterSuccess

def oemRegPage(request):
    return render(request, 'oemRegister.html')
