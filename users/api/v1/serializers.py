from django.contrib.auth import get_user_model
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Read-only representation of a user."""

    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name"]
        read_only_fields = fields


class SignupSerializer(serializers.ModelSerializer):
    """Signup / user creation serializer."""
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["username", "password", "password_confirm"]

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm", None)
        user = User.objects.create_user(
            username=validated_data["username"],
            password=validated_data["password"],
        )
        return user


class LoginSerializer(serializers.Serializer):
    """Login credentials."""
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


class TokenSerializer(serializers.Serializer):
    """JWT token pair."""
    access = serializers.CharField()
    refresh = serializers.CharField()


class AuthResponseSerializer(serializers.Serializer):
    """Combined response serializer for login/signup."""
    user = UserSerializer()
    tokens = TokenSerializer()


class RefreshTokenSerializer(serializers.Serializer):
    """Request serializer for token refresh (only refresh token)."""
    refresh = serializers.CharField()


class AccessTokenSerializer(serializers.Serializer):
    """Response serializer for token refresh (only access token)."""
    access = serializers.CharField()

