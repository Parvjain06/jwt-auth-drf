from django.contrib.auth import get_user_model
from rest_framework import serializers


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(write_only=True)


class CredentialsSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ("id", "username", "email")
        read_only_fields = fields
