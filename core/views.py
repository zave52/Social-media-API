from django.db.models import QuerySet
from rest_framework import generics, viewsets, mixins, serializers

from core.models import Profile
from core.serializers import ProfileSerializer, ProfileListSerializer


class ProfileViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet
):
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer

    def get_serializer_class(self) -> type(serializers.ModelSerializer):
        if self.action == "list":
            return ProfileListSerializer
        return self.serializer_class
