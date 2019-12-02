from django.urls import path, include
from . import views

app_name = 'manager'
urlpatterns = [
    path('', views.index, name='index'),
    path('verRegister', views.verRegPage, name="verRegPage"),
    path('verRegister/register', views.register, name="register"),
    path('verRegister/infos', views.revisionRetrive, name="revisionRetrive"),
    path('verRegister/newRev', views.newRev, name="newRevision")
]
