"""
User Views
==========
API views for user authentication and management.
"""

import logging
from typing import Any

from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from drf_spectacular.utils import extend_schema, OpenApiResponse

from apps.users.models import (
    User,
    UserPreferences,
)
from apps.users.serializers import (
    UserSerializer,
    UserAuthSerializer,
    UserCreateSerializer,
    CareerAITokenObtainPairSerializer,
    TokenRefreshSerializer,
    EmailVerificationSerializer,
    ForgotPasswordSerializer,
    ResetPasswordSerializer,
    ChangePasswordSerializer,
    UserPreferencesSerializer,
)
from apps.users.services import AuthService

logger = logging.getLogger(__name__)


class RegisterView(APIView):
    """
    User registration endpoint.
    
    Creates a new user account and returns JWT tokens.
    """
    
    authentication_classes = []  # No auth required
    permission_classes = [AllowAny]
    serializer_class = UserCreateSerializer

    @extend_schema(
        request=UserCreateSerializer,
        responses={
            201: OpenApiResponse(description="User created successfully"),
            400: OpenApiResponse(description="Validation error"),
            409: OpenApiResponse(description="Email already exists"),
        },
        tags=["auth"],
    )
    def post(self, request: Request) -> Response:
        """Register a new user."""
        serializer = UserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.save()
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        # Send verification email (async)
        if settings.ENABLE_EMAIL_VERIFICATION:
            AuthService.send_verification_email(user)
        
        logger.info(f"New user registered: {user.email}")
        
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserAuthSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(TokenObtainPairView):
    """
    User login endpoint.
    
    Authenticates user and returns JWT tokens.
    """
    
    authentication_classes = []  # No auth required for login
    serializer_class = CareerAITokenObtainPairSerializer

    @extend_schema(
        request=CareerAITokenObtainPairSerializer,
        responses={
            200: OpenApiResponse(description="Login successful"),
            401: OpenApiResponse(description="Invalid credentials"),
            423: OpenApiResponse(description="Account locked"),
            429: OpenApiResponse(description="Too many attempts"),
        },
        tags=["auth"],
    )
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Authenticate user and return tokens."""
        return super().post(request, *args, **kwargs)


class RefreshView(APIView):
    """
    Token refresh endpoint.
    
    Returns a new access token using a valid refresh token.
    """
    
    authentication_classes = []  # No auth required
    permission_classes = [AllowAny]
    serializer_class = TokenRefreshSerializer

    @extend_schema(
        request=TokenRefreshSerializer,
        responses={
            200: OpenApiResponse(description="Token refreshed successfully"),
            401: OpenApiResponse(description="Invalid refresh token"),
        },
        tags=["auth"],
    )
    def post(self, request: Request) -> Response:
        """Refresh access token."""
        serializer = TokenRefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class LogoutView(APIView):
    """
    User logout endpoint.
    
    Blacklists the refresh token.
    """
    
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={
            200: OpenApiResponse(description="Logout successful"),
        },
        tags=["auth"],
    )
    def post(self, request: Request) -> Response:
        """Logout user and blacklist token."""
        try:
            refresh_token = request.data.get("refresh")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
        except Exception as e:
            logger.warning(f"Logout token blacklist failed: {e}")
        
        logger.info(f"User logged out: {request.user.email}")
        
        return Response(
            {"message": "Logout successful."},
            status=status.HTTP_200_OK,
        )


class VerifyEmailView(APIView):
    """
    Email verification endpoint.
    
    Verifies user's email using the token sent via email.
    """
    
    authentication_classes = []  # No auth required
    permission_classes = [AllowAny]
    serializer_class = EmailVerificationSerializer

    @extend_schema(
        request=EmailVerificationSerializer,
        responses={
            200: OpenApiResponse(description="Email verified successfully"),
            400: OpenApiResponse(description="Invalid or expired token"),
            409: OpenApiResponse(description="Email already verified"),
        },
        tags=["auth"],
    )
    def post(self, request: Request) -> Response:
        """Verify user's email."""
        serializer = EmailVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        token = serializer.validated_data["token"]
        user = token.user
        
        if user.is_verified:
            return Response(
                {"message": "Email already verified."},
                status=status.HTTP_409_CONFLICT,
            )
        
        # Verify email
        user.verify_email()
        token.use()
        
        logger.info(f"Email verified for user: {user.email}")
        
        return Response(
            {"message": "Email verified successfully."},
            status=status.HTTP_200_OK,
        )


class ResendVerificationView(APIView):
    """
    Resend verification email endpoint.
    """
    
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={
            200: OpenApiResponse(description="Verification email sent"),
            409: OpenApiResponse(description="Email already verified"),
        },
        tags=["auth"],
    )
    def post(self, request: Request) -> Response:
        """Resend verification email."""
        user = request.user
        
        if user.is_verified:
            return Response(
                {"message": "Email already verified."},
                status=status.HTTP_409_CONFLICT,
            )
        
        AuthService.send_verification_email(user)
        
        return Response(
            {"message": "Verification email sent."},
            status=status.HTTP_200_OK,
        )


class ForgotPasswordView(APIView):
    """
    Forgot password endpoint.
    
    Sends a password reset email to the user.
    """
    
    authentication_classes = []  # No auth required
    permission_classes = [AllowAny]
    serializer_class = ForgotPasswordSerializer

    @extend_schema(
        request=ForgotPasswordSerializer,
        responses={
            200: OpenApiResponse(description="Reset email sent if account exists"),
        },
        tags=["auth"],
    )
    def post(self, request: Request) -> Response:
        """Request password reset."""
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data["email"]
        
        # Always return success to prevent email enumeration
        try:
            user = User.objects.get(email=email)
            AuthService.send_password_reset_email(
                user,
                ip_address=self._get_client_ip(request),
            )
            logger.info(f"Password reset requested for: {email}")
        except User.DoesNotExist:
            logger.info(f"Password reset requested for non-existent email: {email}")
        
        return Response(
            {"message": "If an account exists with this email, a reset link has been sent."},
            status=status.HTTP_200_OK,
        )

    @staticmethod
    def _get_client_ip(request: Request) -> str:
        """Extract client IP from request."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")


class ResetPasswordView(APIView):
    """
    Password reset endpoint.
    
    Resets user's password using the token sent via email.
    """
    
    authentication_classes = []  # No auth required
    permission_classes = [AllowAny]
    serializer_class = ResetPasswordSerializer

    @extend_schema(
        request=ResetPasswordSerializer,
        responses={
            200: OpenApiResponse(description="Password reset successful"),
            400: OpenApiResponse(description="Invalid or expired token"),
        },
        tags=["auth"],
    )
    def post(self, request: Request) -> Response:
        """Reset user's password."""
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        token = serializer.validated_data["token"]
        new_password = serializer.validated_data["new_password"]
        
        user = token.user
        user.set_password(new_password)
        user.save()
        
        token.use()
        
        logger.info(f"Password reset completed for: {user.email}")
        
        return Response(
            {"message": "Password reset successful. You can now login with your new password."},
            status=status.HTTP_200_OK,
        )


class ChangePasswordView(APIView):
    """
    Change password endpoint.
    
    Allows authenticated users to change their password.
    """
    
    permission_classes = [IsAuthenticated]
    serializer_class = ChangePasswordSerializer

    @extend_schema(
        request=ChangePasswordSerializer,
        responses={
            200: OpenApiResponse(description="Password changed successfully"),
            400: OpenApiResponse(description="Validation error"),
        },
        tags=["auth"],
    )
    def post(self, request: Request) -> Response:
        """Change user's password."""
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        user.set_password(serializer.validated_data["new_password"])
        user.save()
        
        logger.info(f"Password changed for: {user.email}")
        
        return Response(
            {"message": "Password changed successfully."},
            status=status.HTTP_200_OK,
        )


class MeView(APIView):
    """
    Current user endpoint.
    
    Returns the authenticated user's profile.
    """
    
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    @extend_schema(
        responses={
            200: UserSerializer,
        },
        tags=["auth"],
    )
    def get(self, request: Request) -> Response:
        """Get current user's profile."""
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class UserPreferencesView(APIView):
    """
    User preferences endpoint.
    """
    
    permission_classes = [IsAuthenticated]
    serializer_class = UserPreferencesSerializer

    @extend_schema(
        responses={
            200: UserPreferencesSerializer,
        },
        tags=["auth"],
    )
    def get(self, request: Request) -> Response:
        """Get user preferences."""
        preferences, _ = UserPreferences.objects.get_or_create(user=request.user)
        serializer = UserPreferencesSerializer(preferences)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        request=UserPreferencesSerializer,
        responses={
            200: UserPreferencesSerializer,
        },
        tags=["auth"],
    )
    def put(self, request: Request) -> Response:
        """Full update of user preferences."""
        preferences, _ = UserPreferences.objects.get_or_create(user=request.user)
        serializer = UserPreferencesSerializer(
            preferences,
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        request=UserPreferencesSerializer,
        responses={
            200: UserPreferencesSerializer,
        },
        tags=["auth"],
    )
    def patch(self, request: Request) -> Response:
        """Update user preferences."""
        preferences, _ = UserPreferences.objects.get_or_create(user=request.user)
        serializer = UserPreferencesSerializer(
            preferences,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response(serializer.data, status=status.HTTP_200_OK)
