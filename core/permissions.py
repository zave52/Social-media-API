from django.http import HttpRequest
from django.views import View
from rest_framework import permissions

from core.models import Commentary, Profile, Post


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit or delete it.
    """

    def has_object_permission(
        self,
        request: HttpRequest,
        view: View,
        obj: Profile | Post | Commentary
    ):
        if request.method in permissions.SAFE_METHODS:
            return True

        if hasattr(obj, "user"):
            return obj.user == request.user

        return obj.author == request.user.profile
