import pathlib
import uuid

from django.contrib.auth import get_user_model
from django.db import models
from django.utils.text import slugify


def post_image_upload(instance: "Post", filename: str) -> pathlib.Path:
    filename = (
        f"{slugify(instance.title)}-{uuid.uuid4}"
        + pathlib.Path(filename).suffix
    )
    return pathlib.Path("upload/posts/") / pathlib.Path(filename)


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

    def __str__(self) -> str:
        return self.title
