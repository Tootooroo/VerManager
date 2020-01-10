from django.urls import path, include
from . import views

app_name = 'manager'
urlpatterns = [
    path('', views.index, name='index'),
    path('verRegister', views.verRegPage, name="verRegPage"),
    path('verRegister/register', views.register, name="register"),
    path('verRegister/infos', views.revisionRetrive, name="revisionRetrive"),
    path('verRegister/verInfos', views.versionRetrive, name="versionRetrive"),
    path('verRegister/newRev', views.newRev, name="newRevision"),
    path('verRegister/verGenPage', views.verGenPage, name="verGenPage"),
    path('verRegister/generation', views.generation, name="generation"),
    path('verRegister/isGenerateDone', views.isGenerationDone, name="isGenerateDone")
]
