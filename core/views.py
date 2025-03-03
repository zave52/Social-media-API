from datetime import datetime

from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.utils.timezone import make_aware
from rest_framework import viewsets, serializers, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.reverse import reverse
from drf_spectacular.utils import extend_schema, OpenApiParameter

from core.tasks import create_scheduled_post
from core.models import Profile, Follow, Post, Like, Commentary
from core.pagination import DefaultPagination
from core.serializers import (
    ProfileSerializer,
    ProfileRetrieveListSerializer,
    FollowSerializer,
    PostSerializer,
    PostListSerializer,
    PostRetrieveSerializer,
    CommentarySerializer
)


class ProfileViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing profiles.
    Provides endpoints for retrieving, updating, deleting, following, and listing profiles.
    """

    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    pagination_class = DefaultPagination
    filter_backends = (filters.SearchFilter,)
    search_fields = ("^username",)

    def get_serializer_class(self) -> type(serializers.ModelSerializer):
        if self.action in ("list", "retrieve", "followings", "followers"):
            return ProfileRetrieveListSerializer
        return self.serializer_class

    @extend_schema(
        summary="Retrieve or modify the current user's profile",
        description=(
            "Allows the authenticated user to GET their profile details, POST (create) a new profile, "
            "PUT/PATCH to update their existing profile, or DELETE their profile."
        ),
        request=ProfileSerializer,
        responses={
            200: ProfileSerializer,
            201: ProfileSerializer,
            204: OpenApiParameter("Profile successfully deleted."),
            400: OpenApiParameter("Validation error."),
            403: OpenApiParameter("Permission denied."),
        }
    )
    @action(
        methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        detail=False,
        url_path="me"
    )
    def my_profile(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        Handle authenticated user's profile:
        - GET: Retrieve profile
        - POST: Create profile
        - PUT/PATCH: Update profile
        - DELETE: Delete profile
        """
        profile = request.user.profile
        if request.method == "GET":
            serializer = ProfileSerializer(profile)
            return Response(serializer.data, status=status.HTTP_200_OK)
        elif request.method == "POST":
            serializer = ProfileSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        elif request.method in ("PUT", "PATCH"):
            self.check_object_permissions(request, profile)
            serializer = ProfileSerializer(
                profile,
                data=request.data,
                partial=(request.method == "PATCH")
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        elif request.method == "DELETE":
            self.check_object_permissions(request, profile)
            profile.delete()
            return Response(
                {"status": "profile deleted"},
                status=status.HTTP_204_NO_CONTENT
            )

    @extend_schema(
        summary="List profiles that the user is following",
        description="Returns a list of profiles that the authenticated user is currently following.",
        responses={
            200: ProfileRetrieveListSerializer(many=True)
        }
    )
    @action(
        methods=["GET"],
        detail=False,
        url_path="followings"
    )
    def followings(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        List of profiles the user is following.
        """
        followings = Follow.objects.filter(follower=request.user.profile)
        self.queryset = self.queryset.filter(
            user__in=followings.values_list("following", flat=True)
        )
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="List followers of the current user",
        description="Returns a list of profiles of users who are following the authenticated user.",
        responses={
            200: ProfileRetrieveListSerializer(many=True)
        }
    )
    @action(
        methods=["GET"],
        detail=False,
        url_path="followers"
    )
    def followers(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        List of profiles following the user.
        """
        followers = Follow.objects.filter(following=request.user.profile)
        self.queryset = self.queryset.filter(
            user__in=followers.values("follower")
        )
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Follow or unfollow a profile",
        description=(
            "Allows the authenticated user to follow or unfollow another profile. "
            "If the user is already following the profile, this will unfollow them."
        ),
        responses={
            201: OpenApiParameter("Status: followed"),
            200: OpenApiParameter("Status: unfollowed"),
            400: OpenApiParameter("Validation error."),
        }
    )
    @action(
        methods=["POST"],
        detail=True,
        url_path="follow"
    )
    def follow(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        Follow or unfollow a profile:
        - If not already following, follow the user.
        - If already following, unfollow the user.
        """
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

    @extend_schema(
        summary="List all profiles",
        description="Retrieve a paginated list of all profiles, including usernames, images, and descriptions.",
        responses={
            200: ProfileRetrieveListSerializer(many=True)
        }
    )
    def list(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        List all available profiles.
        """
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Retrieve a specific profile",
        description="Retrieve details of a specific profile, including username, image, and description.",
        responses={
            200: ProfileRetrieveListSerializer,
            404: OpenApiParameter("Profile not found.")
        }
    )
    def retrieve(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        Retrieve details of a specific profile.
        """
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Create a new profile",
        description="Create a new profile for the authenticated user.",
        request=ProfileSerializer,
        responses={
            201: ProfileSerializer,
            400: OpenApiParameter("Validation Error.")
        },
        parameters=[
            OpenApiParameter(
                name="search",
                description="Search profiles by username. Prefix search "
                            "with `^` for exact match. (ex. ?search=admin)",
                required=False,
                type=str
            )
        ]
    )
    def create(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        Create a new profile for the authenticated user.
        """
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Update an existing profile",
        description="Update an existing profile of the authenticated user.",
        request=ProfileSerializer,
        responses={
            200: ProfileSerializer,
            400: OpenApiParameter("Validation Error."),
            403: OpenApiParameter("Permission denied.")
        }
    )
    def update(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        Update an existing profile for the authenticated user.
        """
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Partially update an existing profile",
        description="Update specific fields in the authenticated user's profile.",
        request=ProfileSerializer,
        responses={
            200: ProfileSerializer,
            400: OpenApiParameter("Validation Error."),
            403: OpenApiParameter("Permission denied.")
        }
    )
    def partial_update(
        self, request: HttpRequest, *args, **kwargs
    ) -> HttpResponse:
        """
        Partially update specific fields in the profile.
        """
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary="Delete a profile",
        description="Delete the authenticated user's profile permanently.",
        responses={
            204: OpenApiParameter("Profile successfully deleted."),
            403: OpenApiParameter("Permission denied.")
        }
    )
    def destroy(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        Permanently delete a profile.
        """
        return super().destroy(request, *args, **kwargs)


class PostViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing posts.
    Provides endpoints for creating, retrieving, updating, deleting, and interacting with posts.
    Additional endpoints include features like liking, commenting, retrieving user-specific posts, and following posts.
    """

    queryset = Post.objects.select_related("author").prefetch_related(
        "tags",
        "likes",
        "comments"
    )
    serializer_class = PostSerializer
    pagination_class = DefaultPagination
    filter_backends = (filters.SearchFilter,)
    search_fields = ("^title", "tags__name")

    def get_queryset(self) -> QuerySet:
        queryset = self.queryset

        if self.action == "retrieve":
            queryset = queryset.prefetch_related("comments__author")

        return queryset

    def get_serializer_class(self) -> type(serializers.ModelSerializer):
        if self.action in ("list", "liked", "my_posts", "following_posts"):
            return PostListSerializer
        if self.action == "retrieve":
            return PostRetrieveSerializer
        return self.serializer_class

    @extend_schema(
        summary="Create a new post",
        description=(
            "Allows the user to create a new post. If a 'publish_time' is provided, "
            "the post will be scheduled for publication at the specified time. "
            "Otherwise, it will be published immediately."
        ),
        responses={
            201: PostSerializer,
            202: OpenApiParameter("Post scheduled for publication."),
            400: OpenApiParameter("Validation error."),
        },
        request=PostSerializer,
    )
    def create(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        if "publish_time" in request.data:
            publish_time_str = request.data.pop("publish_time")
            publish_time = make_aware(
                datetime.strptime(publish_time_str, "%Y-%m-%d %H:%M:%S")
            )

            user_id = request.user.id
            validated_data = request.data.copy()

            create_scheduled_post.apply_async(
                args=(validated_data, user_id),
                eta=publish_time
            )

            return Response(
                {
                    "status": f"Post is scheduled "
                              f"for publication at {publish_time}"
                },
                status=status.HTTP_202_ACCEPTED
            )
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="List user's posts",
        description="Retrieve a list of posts created by the authenticated user.",
        responses={
            200: PostListSerializer(many=True)
        }
    )
    @action(
        methods=["GET"],
        detail=False,
        url_path="my-posts"
    )
    def my_posts(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        List posts authored by the authenticated user.
        """
        user = request.user.profile
        self.queryset = self.queryset.filter(author=user)
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="List posts by followed users",
        description="Retrieve a paginated list of posts authored by users the authenticated user is following.",
        responses={
            200: PostListSerializer(many=True)
        }
    )
    @action(
        methods=["GET"],
        detail=False,
        url_path="following_posts"
    )
    def following_posts(
        self, request: HttpRequest, *args, **kwargs
    ) -> HttpResponse:
        """
        List posts authored by users the authenticated user is following.
        """
        user = request.user.profile
        followings = Follow.objects.filter(follower=user)
        self.queryset = self.queryset.filter(
            author__in=followings.values_list("following", flat=True)
        )
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="List liked posts",
        description="Retrieve a list of posts liked by the authenticated user.",
        responses={
            200: PostListSerializer(many=True)
        }
    )
    @action(
        methods=["GET"],
        detail=False,
        url_path="liked"
    )
    def liked(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        List posts liked by the authenticated user.
        """
        user = request.user.profile
        liked = Like.objects.filter(user=user).values_list(
            "post_id",
            flat=True
        )
        self.queryset = Post.objects.filter(id__in=liked)
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Like or unlike a post",
        description=(
            "Allows the authenticated user to like or unlike a specific post. "
            "If the user has already liked the post, this action will unlike it."
        ),
        responses={
            201: OpenApiParameter("Status: liked"),
            200: OpenApiParameter("Status: unliked"),
            400: OpenApiParameter("Validation error."),
        }
    )
    @action(
        methods=["POST"],
        detail=True,
        url_path="like"
    )
    def like(self, request: HttpRequest, *args, **kwargs) -> Response:
        """
        Like or unlike a specific post.
        """
        post = self.get_object()
        user = request.user.profile

        like, created = Like.objects.get_or_create(post=post, user=user)
        if not created:
            like.delete()
            return Response({"status": "unliked"}, status=status.HTTP_200_OK)

        return Response({"status": "liked"}, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Add a comment to a post",
        description="Allows the authenticated user to add a comment to a specific post.",
        request=CommentarySerializer,
        responses={
            201: CommentarySerializer,
            400: OpenApiParameter("Validation error."),
        }
    )
    @action(
        methods=["POST"],
        detail=True,
        url_path="comment"
    )
    def comment(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        Add a comment to a specific post.
        """
        post = self.get_object()
        serializer = CommentarySerializer(
            data=request.data, context={"request": request, "post": post}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return HttpResponseRedirect(
            reverse("social_media:post-detail", args=[post.id])
        )

    @extend_schema(
        summary="Delete a comment on a post",
        description=(
            "Allows the authenticated user to delete their comment on a specific post. "
            "Returns a 404 error if the comment does not exist or is not owned by the user."
        ),
        responses={
            200: OpenApiParameter("Comment deleted successfully."),
            404: OpenApiParameter("Comment not found or not owned by user.")
        }
    )
    @action(
        methods=["DELETE"],
        detail=True,
        url_path="comment/(?P<pk_comment>[^/.]+)"
    )
    def delete_comment(
        self, request: HttpRequest, pk_comment: int, *args, **kwargs
    ) -> HttpResponse:
        """
        Delete a user's comment from a specific post.
        """
        post = self.get_object()
        user = request.user.profile
        try:
            commentary = post.comments.get(id=pk_comment, author=user)
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

    @extend_schema(
        summary="List all posts",
        description="Retrieve a paginated list of all posts.",
        responses={
            200: PostListSerializer(many=True)
        },
        parameters=[
            OpenApiParameter(
                name="search",
                description="Search posts by title or tag name. Prefix search "
                            "with `^` for exact match. (ex. ?search=tag)",
                required=False,
                type=str
            )
        ]
    )
    def list(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        List all available posts.
        """
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Retrieve a specific post",
        description="Retrieve details of a specific post, "
                    "including comments, likes, and tags.",
        responses={
            200: PostRetrieveSerializer,
            404: OpenApiParameter("Post not found.")
        }
    )
    def retrieve(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        Retrieve details of a specific post.
        """
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Update an existing post",
        description="Update an existing post created by the authenticated user.",
        request=PostSerializer,
        responses={
            200: PostSerializer,
            400: OpenApiParameter("Validation error."),
            403: OpenApiParameter("Permission denied.")
        }
    )
    def update(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        Update an existing post.
        """
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Partially update an existing post",
        description="Update specific fields of an existing post.",
        request=PostSerializer,
        responses={
            200: PostSerializer,
            400: OpenApiParameter("Validation error."),
            403: OpenApiParameter("Permission denied.")
        }
    )
    def partial_update(
        self, request: HttpRequest, *args, **kwargs
    ) -> HttpResponse:
        """
        Partially update specific fields of a post.
        """
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary="Delete a post",
        description="Delete an existing post created by the authenticated user.",
        responses={
            204: OpenApiParameter("Post successfully deleted."),
            403: OpenApiParameter("Permission denied."),
        }
    )
    def destroy(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        Permanently delete a post.
        """
        return super().destroy(request, *args, **kwargs)
