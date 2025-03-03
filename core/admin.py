from django.contrib import admin

from core.models import Profile, Post, Follow, Like, Commentary, Tag

admin.register(Profile)
admin.register(Post)
admin.register(Follow)
admin.register(Like)
admin.register(Commentary)
admin.register(Tag)
