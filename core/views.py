from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from rest_framework import viewsets, mixins, serializers
from rest_framework.decorators import action
from rest_framework.reverse import reverse

from core.models import Profile, Follow, Post, Like
from core.serializers import (
    ProfileSerializer,
    ProfileListSerializer,
    FollowSerializer,
    PostSerializer,
    PostListSerializer,
    PostRetrieveSerializer
)


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

    @action(
        methods=["GET"],
        detail=False,
        url_path="me"
    )
    def my_profile(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        profile = request.user.profile
        return HttpResponseRedirect(
            reverse("core:profile-detail", args=[profile.id])
        )

    @action(
        methods=["GET"],
        detail=False,
        url_path="followings"
    )
    def followings(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        followings = Follow.objects.filter(follower=request.user)
        self.queryset = self.queryset.filter(
            user__in=followings.values_list("following", flat=True)
        )
        return super().list(request, *args, **kwargs)

    @action(
        methods=["GET"],
        detail=False,
        url_path="followers"
    )
    def followers(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        followers = Follow.objects.filter(following=request.user)
        self.queryset = self.queryset.filter(
            user__in=followers.values("follower")
        )
        return super().list(request, *args, **kwargs)

    @action(
        methods=["GET"],
        detail=True,
        url_path="follow"
    )
    def follow(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        profile = self.get_object()
        user = request.user

        follow_data = {
            "follower": user.id,
            "following": profile.user.id
        }

        serializer = FollowSerializer(data=follow_data)
        serializer.is_valid(raise_exception=True)

        relation = Follow.objects.filter(follower=user, following=profile.user)
        if not relation.exists():
            serializer.save()
        else:
            relation.delete()

        return HttpResponseRedirect(
            reverse("core:profile-detail", args=[profile.id])
        )
