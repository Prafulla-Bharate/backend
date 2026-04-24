"""
User Serializers
================
Serializers for user authentication and profile management.
"""

from typing import Any, Dict

from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.exceptions import (
    AccountLockedException,
    UnauthorizedException,
)
from apps.users.models import (
    User,
    UserPreferences,
    LoginAttempt,
    EmailVerificationToken,
    PasswordResetToken,
)


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model."""
    
    full_name = serializers.CharField(read_only=True)
    is_profile_complete = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "phone",
            "location",
            "bio",
            "linkedin_url",
            "github_url",
            "portfolio_url",
            "experience_level",
            "is_verified",
            "is_profile_complete",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "email", "is_verified", "created_at", "updated_at"]


class UserAuthSerializer(serializers.ModelSerializer):
    """Minimal serializer for auth responses (login/register)."""
    
    is_profile_complete = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "is_profile_complete",
        ]
        read_only_fields = fields


class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""
    
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={"input_type": "password"},
    )
    password_confirm = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
    )
    
    class Meta:
        model = User
        fields = [
            "email",
            "password",
            "password_confirm",
            "first_name",
            "last_name",
        ]

    def validate_email(self, value: str) -> str:
        """Validate email is not already registered."""
        email = value.lower().strip()
        if User.all_objects.filter(email=email).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return email

    def validate_password(self, value: str) -> str:
        """Validate password strength."""
        validate_password(value)
        return value

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        """Validate password confirmation matches."""
        if attrs.get("password") != attrs.get("password_confirm"):
            raise serializers.ValidationError(
                {"password_confirm": "Passwords do not match."}
            )
        return attrs

    def create(self, validated_data: Dict[str, Any]) -> User:
        """Create and return the user."""
        validated_data.pop("password_confirm")
        user = User.objects.create_user(**validated_data)
        
        # UserPreferences is created automatically via signal
        
        return user


class CareerAITokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom JWT token serializer with user data."""
    
    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        """Validate credentials and return tokens with user data."""
        email = attrs.get("email", "").lower().strip()
        password = attrs.get("password", "")
        
        # Get client info
        request = self.context.get("request")
        ip_address = self._get_client_ip(request) if request else None
        user_agent = request.META.get("HTTP_USER_AGENT", "") if request else ""
        
        # Check for lockout
        if LoginAttempt.is_locked_out(email, ip_address or ""):
            raise AccountLockedException(
                "Account temporarily locked due to too many failed login attempts. "
                "Please try again in 15 minutes."
            )
        
        # Authenticate
        user = authenticate(
            request=request,
            username=email,
            password=password,
        )
        
        # Log attempt
        LoginAttempt.objects.create(
            email=email,
            ip_address=ip_address or "0.0.0.0",
            user_agent=user_agent,
            successful=user is not None,
        )
        
        if user is None:
            raise UnauthorizedException("Invalid email or password.")
        
        if not user.is_active:
            raise UnauthorizedException("Account is inactive.")
        
        # Generate tokens
        # (SimpleJWT UPDATE_LAST_LOGIN=True handles last_login automatically)
        refresh = RefreshToken.for_user(user)

        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserAuthSerializer(user).data,
        }

    @staticmethod
    def _get_client_ip(request) -> str:
        """Extract client IP from request."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")

    @classmethod
    def get_token(cls, user: User) -> RefreshToken:
        """Get token for user with custom claims."""
        token = super().get_token(user)
        
        # Add custom claims
        token["email"] = user.email
        token["first_name"] = user.first_name
        token["last_name"] = user.last_name
        token["is_verified"] = user.is_verified
        
        return token


class TokenRefreshSerializer(serializers.Serializer):
    """Serializer for token refresh."""
    
    refresh = serializers.CharField()

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        """Validate refresh token and return new tokens (with rotation)."""
        from rest_framework_simplejwt.tokens import RefreshToken
        from rest_framework_simplejwt.exceptions import TokenError
        
        try:
            refresh = RefreshToken(attrs["refresh"])
            data = {
                "access": str(refresh.access_token),
            }
            # Token rotation - issue new refresh token and blacklist old
            if hasattr(refresh, "set_jti") and hasattr(refresh, "set_exp"):
                new_refresh = RefreshToken.for_user(
                    User.objects.get(id=refresh.payload.get("user_id"))
                )
                data["refresh"] = str(new_refresh)
                try:
                    refresh.blacklist()
                except Exception:
                    pass  # Blacklisting may fail if not configured
            else:
                data["refresh"] = str(refresh)
            return data
        except TokenError as e:
            raise serializers.ValidationError({"refresh": str(e)})


class EmailVerificationSerializer(serializers.Serializer):
    """Serializer for email verification."""
    
    token = serializers.CharField()

    def validate_token(self, value: str) -> EmailVerificationToken:
        """Validate verification token."""
        try:
            token = EmailVerificationToken.objects.get(token=value)
        except EmailVerificationToken.DoesNotExist:
            raise serializers.ValidationError("Invalid verification token.")
        
        if not token.is_valid:
            raise serializers.ValidationError("Token has expired or already been used.")
        
        return token


class ForgotPasswordSerializer(serializers.Serializer):
    """Serializer for forgot password request."""
    
    email = serializers.EmailField()

    def validate_email(self, value: str) -> str:
        """Normalize email."""
        return value.lower().strip()


class ResetPasswordSerializer(serializers.Serializer):
    """Serializer for password reset."""
    
    token = serializers.CharField()
    new_password = serializers.CharField(min_length=8, write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate_token(self, value: str) -> PasswordResetToken:
        """Validate reset token."""
        try:
            token = PasswordResetToken.objects.get(token=value)
        except PasswordResetToken.DoesNotExist:
            raise serializers.ValidationError("Invalid reset token.")
        
        if not token.is_valid:
            raise serializers.ValidationError("Token has expired or already been used.")
        
        return token

    def validate_new_password(self, value: str) -> str:
        """Validate new password strength."""
        validate_password(value)
        return value

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        """Validate password confirmation."""
        if attrs.get("new_password") != attrs.get("confirm_password"):
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match."}
            )
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for password change."""
    
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(min_length=8, write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate_current_password(self, value: str) -> str:
        """Validate current password."""
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate_new_password(self, value: str) -> str:
        """Validate new password strength."""
        validate_password(value)
        return value

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        """Validate password confirmation and that new password is different."""
        if attrs.get("new_password") != attrs.get("confirm_password"):
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match."}
            )
        
        if attrs.get("current_password") == attrs.get("new_password"):
            raise serializers.ValidationError(
                {"new_password": "New password must be different from current password."}
            )
        
        return attrs


class UserPreferencesSerializer(serializers.ModelSerializer):
    """Serializer for user preferences."""
    
    class Meta:
        model = UserPreferences
        fields = [
            "theme",
            "language",
            "timezone",
            "email_notifications",
            "deadline_reminders",
            "streak_reminders",
            "job_alerts",
            "learning_updates",
            "interview_reminders",
            "achievement_notifications",
        ]
