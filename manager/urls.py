from django.urls import path, include
from . import views

app_name = 'manager'
urlpatterns = [
    path('', views.index, name='index'),
    path('verManager', views.verManagerPage, name="verMngPage"),
    path('verRegister/register', views.register, name="register"),
    path('verRegister/infos', views.revisionRetrive, name="revisionRetrive"),
    path('verRegister/verInfos', views.versionRetrive, name="versionRetrive"),
    path('verRegister/newRev', views.newRev, name="newRevision"),
    path('verRegister/generation', views.generation, name="generation"),
    path('verRegister/isGenerateDone',
         views.isGenerationDone, name="isGenerateDone"),
    path('verRegister/tempGen/<str:revision>',
         views.temporaryGen, name="tempVerGen")
]
