from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(
    post_save,
    sender=get_user_model()
)
def create_user_profile(
    sender: type,
    instance: get_user_model(),
    created: bool,
    **kwargs
) -> None:
    if created:
        from core.models import Profile
        Profile.objects.create(user=instance)
