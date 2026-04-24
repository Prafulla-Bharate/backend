"""
User Models
===========
Custom user model and related authentication models.
"""

import hashlib
import secrets
import uuid
from typing import Optional

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel, UUIDModel, SoftDeleteModel, SoftDeleteManager


class UserManager(BaseUserManager):
    """Custom manager for User model with soft delete support."""
    
    def get_queryset(self):
        """Return queryset excluding soft-deleted users."""
        return super().get_queryset().filter(deleted_at__isnull=True)
    
    def create_user(
        self,
        email: str,
        password: str,
        first_name: str = "",
        last_name: str = "",
        **extra_fields
    ) -> "User":
        """Create and save a regular user."""
        if not email:
            raise ValueError("Email is required")
        
        email = self.normalize_email(email)
        user = self.model(
            email=email,
            first_name=first_name,
            last_name=last_name,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(
        self,
        email: str,
        password: str,
        first_name: str = "",
        last_name: str = "",
        **extra_fields
    ) -> "User":
        """Create and save a superuser."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_verified", True)
        
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        
        return self.create_user(email, password, first_name, last_name, **extra_fields)

    @staticmethod
    def normalize_email(email: str) -> str:
        """Normalize email address."""
        email = email.lower().strip()
        return email
    
    def with_deleted(self):
        """Include soft-deleted records in the queryset."""
        return super().get_queryset()

    def only_deleted(self):
        """Return only soft-deleted records."""
        return super().get_queryset().filter(deleted_at__isnull=False)


class User(UUIDModel, AbstractBaseUser, PermissionsMixin, TimeStampedModel, SoftDeleteModel):
    """
    Custom User model using email as the unique identifier.
    
    Features:
    - UUID primary key for security
    - Email-based authentication
    - Soft delete support
    - Profile information
    - Verification status
    """
    
    EXPERIENCE_LEVELS = [
        ("student", "Student"),
        ("entry", "Entry Level (0-2 years)"),
        ("mid", "Mid Level (2-5 years)"),
        ("senior", "Senior Level (5-10 years)"),
        ("lead", "Lead/Manager (10+ years)"),
        ("executive", "Executive"),
    ]
    
    # Core fields
    email = models.EmailField(
        unique=True,
        max_length=255,
        db_index=True,
        help_text="User's email address (used for login)",
    )
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    
    # Profile fields
    phone = models.CharField(max_length=20, blank=True)
    location = models.CharField(max_length=255, blank=True)
    bio = models.TextField(blank=True)
    linkedin_url = models.URLField(max_length=500, blank=True)
    github_url = models.URLField(max_length=500, blank=True)
    portfolio_url = models.URLField(max_length=500, blank=True)
    experience_level = models.CharField(
        max_length=50,
        choices=EXPERIENCE_LEVELS,
        blank=True,
    )
    
    # Status fields
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_verified = models.BooleanField(
        default=False,
        help_text="Whether email has been verified",
    )
    email_verified_at = models.DateTimeField(null=True, blank=True)
    last_login = models.DateTimeField(null=True, blank=True)
    
    objects = UserManager()
    all_objects = models.Manager()
    
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        db_table = "users"
        verbose_name = "User"
        verbose_name_plural = "Users"
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["is_active", "is_verified"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return self.email

    @property
    def full_name(self) -> str:
        """Return user's full name."""
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def is_profile_complete(self) -> bool:
        """Check if user has completed their profile."""
        required_fields = [
            self.first_name,
            self.last_name,
        ]
        return all(required_fields)

    def verify_email(self) -> None:
        """Mark email as verified."""
        self.is_verified = True
        self.email_verified_at = timezone.now()
        self.save(update_fields=["is_verified", "email_verified_at", "updated_at"])


class UserToken(UUIDModel, TimeStampedModel):
    """
    Model for managing JWT tokens and sessions.
    
    Stores token hashes for revocation and session tracking.
    """
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="tokens",
    )
    access_token_hash = models.CharField(max_length=500)
    refresh_token_hash = models.CharField(max_length=500)
    expires_at = models.DateTimeField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "user_tokens"
        indexes = [
            models.Index(fields=["user", "expires_at"]),
            models.Index(fields=["refresh_token_hash"]),
        ]

    @property
    def is_revoked(self) -> bool:
        """Check if token is revoked."""
        return self.revoked_at is not None

    @property
    def is_expired(self) -> bool:
        """Check if token is expired."""
        return timezone.now() > self.expires_at

    def revoke(self) -> None:
        """Revoke this token."""
        self.revoked_at = timezone.now()
        self.save(update_fields=["revoked_at"])

    @staticmethod
    def hash_token(token: str) -> str:
        """Create a hash of a token for storage."""
        return hashlib.sha256(token.encode()).hexdigest()


class UserPreferences(UUIDModel, TimeStampedModel):
    """
    User preferences and settings.
    """
    
    THEMES = [
        ("dark", "Dark"),
        ("light", "Light"),
        ("system", "System"),
    ]
    
    LANGUAGES = [
        ("en", "English"),
        ("es", "Spanish"),
        ("fr", "French"),
        ("de", "German"),
        ("zh", "Chinese"),
    ]
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="preferences",
    )
    theme = models.CharField(max_length=20, choices=THEMES, default="dark")
    language = models.CharField(max_length=20, choices=LANGUAGES, default="en")
    timezone = models.CharField(max_length=50, default="UTC")

    # Career selection
    accepted_career_title = models.CharField(
        max_length=255,
        blank=True,
        help_text="The career title the user has accepted from their prediction"
    )

    # Notification preferences
    email_notifications = models.BooleanField(default=True)
    deadline_reminders = models.BooleanField(default=True)
    streak_reminders = models.BooleanField(default=True)
    job_alerts = models.BooleanField(default=True)
    learning_updates = models.BooleanField(default=True)
    interview_reminders = models.BooleanField(default=True)
    achievement_notifications = models.BooleanField(default=True)

    class Meta:
        db_table = "user_preferences"
        verbose_name = "User Preferences"
        verbose_name_plural = "User Preferences"

    def __str__(self) -> str:
        return f"Preferences for {self.user.email}"


class EmailVerificationToken(UUIDModel, TimeStampedModel):
    """
    Email verification token model.
    """
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="verification_tokens",
    )
    token = models.CharField(max_length=255, unique=True, db_index=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "email_verification_tokens"

    @property
    def is_valid(self) -> bool:
        """Check if token is valid."""
        return self.used_at is None and timezone.now() < self.expires_at

    def use(self) -> None:
        """Mark token as used."""
        self.used_at = timezone.now()
        self.save(update_fields=["used_at"])

    @classmethod
    def create_for_user(cls, user: User, hours_valid: int = 24) -> "EmailVerificationToken":
        """Create a new verification token for a user."""
        token = secrets.token_urlsafe(32)
        return cls.objects.create(
            user=user,
            token=token,
            expires_at=timezone.now() + timezone.timedelta(hours=hours_valid),
        )


class PasswordResetToken(UUIDModel, TimeStampedModel):
    """
    Password reset token model.
    """
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="password_reset_tokens",
    )
    token = models.CharField(max_length=255, unique=True, db_index=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        db_table = "password_reset_tokens"

    @property
    def is_valid(self) -> bool:
        """Check if token is valid."""
        return self.used_at is None and timezone.now() < self.expires_at

    def use(self) -> None:
        """Mark token as used."""
        self.used_at = timezone.now()
        self.save(update_fields=["used_at"])

    @classmethod
    def create_for_user(
        cls,
        user: User,
        hours_valid: int = 2,
        ip_address: Optional[str] = None
    ) -> "PasswordResetToken":
        """Create a new password reset token for a user."""
        token = secrets.token_urlsafe(32)
        return cls.objects.create(
            user=user,
            token=token,
            expires_at=timezone.now() + timezone.timedelta(hours=hours_valid),
            ip_address=ip_address,
        )


class LoginAttempt(UUIDModel, TimeStampedModel):
    """
    Track login attempts for security and rate limiting.
    """
    
    email = models.EmailField(db_index=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    successful = models.BooleanField(default=False)

    class Meta:
        db_table = "login_attempts"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["email", "created_at"]),
            models.Index(fields=["ip_address", "created_at"]),
        ]

    @classmethod
    def get_failed_attempts_count(
        cls,
        email: str,
        ip_address: str,
        minutes: int = 15
    ) -> int:
        """Get count of failed login attempts in the last N minutes."""
        since = timezone.now() - timezone.timedelta(minutes=minutes)
        return cls.objects.filter(
            models.Q(email=email) | models.Q(ip_address=ip_address),
            successful=False,
            created_at__gte=since,
        ).count()

    @classmethod
    def is_locked_out(
        cls,
        email: str,
        ip_address: str,
        max_attempts: int = 5,
        lockout_minutes: int = 15
    ) -> bool:
        """Check if the account/IP is locked out."""
        return cls.get_failed_attempts_count(
            email, ip_address, lockout_minutes
        ) >= max_attempts
