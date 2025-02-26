import pathlib
import uuid

from django.contrib.auth import get_user_model
from django.db import models
from django.utils.text import slugify


def image_upload(
    instance: models.Model,
    filename: str,
    path: str
) -> pathlib.Path:
    filename = (
        f"{slugify(instance)}-{uuid.uuid4}"
        + pathlib.Path(filename).suffix
    )
    return pathlib.Path(path) / pathlib.Path(filename)


def post_image_upload(instance: "Post", filename: str) -> pathlib.Path:
    return image_upload(instance, filename, "upload/posts/")


def profile_image_upload(instance: "Profile", filename: str) -> pathlib.Path:
    return image_upload(instance, filename, "upload/profiles/")


class Tag(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self) -> str:
        return self.name


class Post(models.Model):
    title = models.CharField(max_length=255)
    text = models.TextField()
    image = models.ImageField(
        null=True,
        blank=True,
        upload_to=post_image_upload
    )
    owner = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name="posts"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    tags = models.ForeignKey(
        Tag,
        on_delete=models.CASCADE,
        related_name="posts"
    )

    def __str__(self) -> str:
        return self.title


class Profile(models.Model):
    class PrivacySettings(models.TextChoices):
        PUBLIC = "public"
        PRIVATE = "private"

    user = models.OneToOneField(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name="profile"
    )
    image_profile = models.ImageField(
        blank=True,
        null=True,
        upload_to=profile_image_upload
    )
    description = models.TextField(blank=True, null=True)
    privacy_settings = models.CharField(
        max_length=7,
        choices=PrivacySettings,
        default=PrivacySettings.PUBLIC
    )

    def __str__(self) -> str:
        return f"{self.user.username} profile"
