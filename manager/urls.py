from django.urls import path, include
from rest_framework import routers
from .views import VersionViewSet, RevisionViewSet
from . import views

app_name = 'manager'

router = routers.SimpleRouter()
router.register(r'versions', VersionViewSet)
router.register(r'revisions', RevisionViewSet)

urlpatterns = [
    path('', views.index, name='index'),
    path('verManager', views.verManagerPage, name="verMngPage"),
    path('verRegister/newRev', views.newRev, name="newRevision"),
    path('api/', include(router.urls))
]
