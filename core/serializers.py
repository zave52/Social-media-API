from rest_framework import serializers

from core.models import Tag, Post, Profile, Like, Commentary, Follow


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ("id", "name")
