from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from rest_framework import viewsets, mixins, serializers, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.reverse import reverse

from core.models import Profile, Follow, Post, Like, Commentary
from core.permissions import IsOwnerOrReadOnly
from core.serializers import (
    ProfileSerializer,
    ProfileRetrieveListSerializer,
    FollowSerializer,
    PostSerializer,
    PostListSerializer,
    PostRetrieveSerializer,
    CommentarySerializer
)


class ProfileViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet
):
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    permission_classes = (IsAuthenticated,)

    def get_permissions(self) -> tuple:
        if self.action in ("update", "partial_update"):
            return IsAuthenticated, IsOwnerOrReadOnly
        return self.permission_classes

    def get_serializer_class(self) -> type(serializers.ModelSerializer):
        if self.action in ("list", "retrieve", "followings", "followers"):
            return ProfileRetrieveListSerializer
        return self.serializer_class

    @action(
        methods=["GET", "PATCH"],
        detail=False,
        url_path="me"
    )
    def my_profile(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        self.check_permissions(request)

        profile = request.user.profile
        if request.method == "GET":
            return HttpResponseRedirect(
                reverse("social_media:profile-detail", args=[profile.id])
            )
        elif request.method == "PATCH":
            self.check_object_permissions(request, profile)

            serializer = ProfileSerializer(
                profile,
                data=request.data,
                partial=True
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        methods=["GET"],
        detail=False,
        url_path="followings"
    )
    def followings(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        self.check_permissions(request)

        followings = Follow.objects.filter(follower=request.user.profile)
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
        self.check_permissions(request)

        followers = Follow.objects.filter(following=request.user.profile)
        self.queryset = self.queryset.filter(
            user__in=followers.values("follower")
        )
        return super().list(request, *args, **kwargs)

    @action(
        methods=["POST"],
        detail=True,
        url_path="follow"
    )
    def follow(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        self.check_permissions(request)

        profile = self.get_object()
        user = request.user.profile

        follow_data = {
            "follower": user.id,
            "following": profile.id
        }

        serializer = FollowSerializer(data=follow_data)
        serializer.is_valid(raise_exception=True)

        relation = Follow.objects.filter(
            follower=user.profile,
            following=profile
        )
        if not relation.exists():
            serializer.save()
            return Response(
                {"status": "followed"},
                status=status.HTTP_201_CREATED
            )
        else:
            relation.delete()
            return Response({"status": "unfollowed"}, status=status.HTTP_200_OK)


class PostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    permission_classes = (IsAuthenticated,)

    def get_permissions(self) -> tuple:
        if self.action in (
            "update", "partial_update", "destroy", "delete_comment"
        ):
            return IsAuthenticated, IsOwnerOrReadOnly
        return self.permission_classes

    def get_serializer_class(self) -> type(serializers.ModelSerializer):
        if self.action in ("list", "liked", "my_posts", "following_posts"):
            return PostListSerializer
        if self.action == "retrieve":
            return PostRetrieveSerializer
        return self.serializer_class

    @action(
        methods=["GET"],
        detail=False,
        url_path="my-posts"
    )
    def my_posts(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        self.check_permissions(request)

        user = request.user.profile
        self.queryset = self.queryset.filter(author=user)
        return super().list(request, *args, **kwargs)

    @action(
        methods=["GET"],
        detail=False,
        url_path="following_posts"
    )
    def following_posts(
        self, request: HttpRequest, *args, **kwargs
    ) -> HttpResponse:
        self.check_permissions(request)

        user = request.user.profile
        followings = Follow.objects.filter(follower=user)
        self.queryset = self.queryset.filter(
            author__in=followings.values_list("following", flat=True)
        )
        return super().list(request, *args, **kwargs)

    @action(
        methods=["GET"],
        detail=False,
        url_path="liked"
    )
    def liked(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        self.check_permissions(request)

        user = request.user.profile
        liked = Like.objects.filter(user=user).values_list(
            "post_id",
            flat=True
        )
        self.queryset = Post.objects.filter(id__in=liked)
        return super().list(request, *args, **kwargs)

    @action(
        methods=["POST"],
        detail=True,
        url_path="like"
    )
    def like(self, request: HttpRequest, *args, **kwargs) -> Response:
        self.check_permissions(request)

        post = self.get_object()
        user = request.user.profile

        like, created = Like.objects.get_or_create(post=post, user=user)
        if not created:
            like.delete()
            return Response({"status": "unliked"}, status=status.HTTP_200_OK)

        return Response({"status": "liked"}, status=status.HTTP_201_CREATED)

    @action(
        methods=["POST"],
        detail=True,
        url_path="comment"
    )
    def comment(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        self.check_permissions(request)

        post = self.get_object()
        serializer = CommentarySerializer(
            data=request.data, context={"request": request, "post": post}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return HttpResponseRedirect(
            reverse("social_media:post-detail", args=[post.id])
        )

    @action(
        methods=["DELETE"],
        detail=True,
        url_path="comment/(?P<pk_comment>[^/.]+)"
    )
    def delete_comment(
        self, request: HttpRequest, pk_comment: int, *args, **kwargs
    ) -> HttpResponse:
        post = self.get_object()
        user = request.user.profile
        try:
            commentary = post.comments.get(id=pk_comment, author=user)

            self.check_object_permissions(request, commentary)

            commentary.delete()
            return Response(
                {"status": "comment deleted"},
                status=status.HTTP_200_OK
            )
        except Commentary.DoesNotExist:
            return Response(
                {"error": "Commentary not found or not owned by user."},
                status=status.HTTP_404_NOT_FOUND
            )
