from django.contrib.auth import get_user_model
from rest_framework import serializers
from django.utils.translation import gettext as _


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ("id", "email", "password", "is_staff")
        read_only_fields = ("id", "is_staff")
        extra_kwargs = {
            "password": {
                "write_only": True,
                "min_length": 5,
                "style": {"input_type": "password"},
                "label": _("Password"),
            }
        }

    def create(self, validated_data: dict) -> get_user_model():
        """Create user with encrypted password"""
        return get_user_model().objects.create_user(**validated_data)

    def update(
        self, instance: get_user_model(), validated_data: dict
    ) -> get_user_model():
        """Update user with encrypted password"""
        password = validated_data.get("password", None)
        user = super().update(instance, validated_data)

        if password:
            user.set_password(password)
            user.save()

        return user
