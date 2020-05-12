from .models import Versions, Revisions
from rest_framework import serializers


class VersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Versions
        fields = ['vsn', 'sn', 'dateTime']


class RevisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Revisions
        fields = ['sn', 'author', 'comment', 'dateTime']


class VersionInfoSerializer(serializers.Serializer):
    vsn = serializers.CharField(max_length=512)
    sn = serializers.CharField(max_length=512)


class BuildInfoSerializer(serializers.Serializer):
    log_from = serializers.CharField(max_length=60)
    log_to = serializers.CharField(max_length=60)
