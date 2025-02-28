from django.urls import include, path
from rest_framework import routers

from core.views import ProfileViewSet, PostViewSet

router = routers.DefaultRouter()

router.register("profiles", ProfileViewSet)
router.register("posts", PostViewSet)

urlpatterns = [
    path("", include(router.urls))
]

app_name = "social_media"
