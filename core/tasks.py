from celery import shared_task
from django.contrib.auth import get_user_model

from core.models import Profile
from core.serializers import PostSerializer


@shared_task
def create_scheduled_post(validated_data: dict, user_id: int) -> str:
    """
    This task creates a post at a scheduled time
    """

    class MockRequest:
        def __init__(self, user: get_user_model()) -> None:
            self.user = user

    try:
        user = get_user_model().objects.get(id=user_id)
        mock_request = MockRequest(user)

        serializer = PostSerializer(
            data=validated_data,
            context={"request": mock_request}
        )
        if serializer.is_valid():
            serializer.save()
            return f"Post '{serializer.data['title']}' created successfully"
        return f"Validation failed. Error: {serializer.errors}"
    except Profile.DoesNotExist:
        return "Profile not found"
    except Exception as e:
        return f"Error: {str(e)}"
