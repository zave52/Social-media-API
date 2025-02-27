from rest_framework import serializers
from rest_framework.relations import SlugRelatedField

from core.models import Tag, Post, Profile, Like, Commentary, Follow


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ("id", "name")


class PostSerializer(serializers.ModelSerializer):
    tags = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Post
        fields = (
            "id", "title", "content", "author", "image", "created_at", "tags"
        )
        read_only_fields = ("id", "author", "created_at")

    @staticmethod
    def handle_tag_creation(validated_data: dict) -> dict:
        if "tags" in validated_data:
            tags = [tag for tag in validated_data.pop("tags").split()]
            for tag in tags:
                new_tag, _ = Tag.objects.get_or_create(name=tag)
                validated_data["tags"].append(new_tag)
        return validated_data

    def create(self, validated_data: dict) -> Post:
        validated_data = PostSerializer.handle_tag_creation(validated_data)
        return super().create(validated_data)

    def update(self, instance: Post, validated_data: dict) -> Post:
        validated_data = PostSerializer.handle_tag_creation(validated_data)
        return super().update(instance, validated_data)


class ProfileListSerializer(serializers.ModelSerializer):
    username = SlugRelatedField(
        read_only=True,
        slug_field="username",
        source="user"
    )

    class Meta:
        model = Profile
        fields = (
            "id", "username", "image_profile", "description", "privacy_settings"
        )


class LikeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Like
        fields = ("id", "post", "user")


class CommentarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Commentary
        fields = ("id", "post", "author", "content")


class FollowSerializer(serializers.ModelSerializer):
    class Meta:
        model = Follow
        fields = ("id", "follower", "following")
