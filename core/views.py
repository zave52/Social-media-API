from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from rest_framework import viewsets, mixins, serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.reverse import reverse

from core.models import Profile, Follow, Post, Like, Commentary
from core.serializers import (
    ProfileSerializer,
    ProfileListSerializer,
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
            reverse("social_media:profile-detail", args=[profile.id])
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
            reverse("social_media:profile-detail", args=[profile.id])
        )


class PostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.all()
    serializer_class = PostSerializer

    def get_serializer_class(self) -> type(serializers.ModelSerializer):
        if self.action == "list":
            return PostListSerializer
        if self.action == "retrieve":
            return PostRetrieveSerializer
        return self.serializer_class

    @action(
        methods=["GET", "POST"],
        detail=False,
        url_path="my-posts"
    )
    def my_posts(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        user = request.user
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
        user = request.user
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
        user = request.user
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
        post = self.get_object()
        user = request.user

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
        try:
            commentary = post.comments.get(id=pk_comment, author=request.user)
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
