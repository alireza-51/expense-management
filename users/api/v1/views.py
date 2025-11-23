from django.contrib.auth import authenticate, get_user_model
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from drf_spectacular.utils import extend_schema, OpenApiResponse

from .serializers import (
    SignupSerializer,
    LoginSerializer,
    UserSerializer,
    TokenSerializer,
    AuthResponseSerializer,
    RefreshTokenSerializer,
    AccessTokenSerializer

)

User = get_user_model()


def get_tokens_for_user(user):
    """Helper to create JWT token pair."""
    refresh = RefreshToken.for_user(user)
    return {"refresh": str(refresh), "access": str(refresh.access_token)}


@extend_schema(tags=["auth"])
class SignupView(APIView):
    """Register a new user and return JWT tokens."""
    permission_classes = [AllowAny]

    @extend_schema(
        request=SignupSerializer,
        responses={
            201: OpenApiResponse(
                response=AuthResponseSerializer,
                description="User created successfully with JWT tokens",
            )
        },
    )
    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        tokens = get_tokens_for_user(user)
        return Response(
            {"user": UserSerializer(user).data, "tokens": tokens},
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["auth"])
class LoginView(APIView):
    """Authenticate user and return JWT tokens."""
    permission_classes = [AllowAny]

    @extend_schema(
        request=LoginSerializer,
        responses={
            200: OpenApiResponse(
                response=AuthResponseSerializer,
                description="User authenticated successfully with JWT tokens",
            ),
            401: OpenApiResponse(description="Invalid credentials"),
        },
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            username=serializer.validated_data["username"],
            password=serializer.validated_data["password"],
        )
        if not user:
            return Response({"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
        if not user.is_active:
            return Response({"detail": "User account is disabled"}, status=status.HTTP_403_FORBIDDEN)

        tokens = get_tokens_for_user(user)
        return Response(
            {"user": UserSerializer(user).data, "tokens": tokens},
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["auth"])
class LogoutView(APIView):
    """Blacklist refresh token to logout."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=TokenSerializer,
        responses={
            200: OpenApiResponse(description="Logout successful"),
            400: OpenApiResponse(description="Invalid or missing refresh token"),
        },
    )
    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response({"detail": "Refresh token required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception:
            return Response({"detail": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"detail": "Logged out successfully"}, status=status.HTTP_200_OK)


@extend_schema(tags=["auth"])
class MeView(APIView):
    """Return current user profile."""
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=UserSerializer)
    def get(self, request):
        return Response(UserSerializer(request.user).data)


@extend_schema(
    tags=["auth"],
    request=RefreshTokenSerializer,
    responses={
        200: OpenApiResponse(
            response=AccessTokenSerializer,
            description="New access token issued successfully",
        ),
        401: OpenApiResponse(description="Invalid or expired refresh token"),
    },
)
class CustomTokenRefreshView(TokenRefreshView):
    """Refresh JWT access token using a valid refresh token."""
    pass
