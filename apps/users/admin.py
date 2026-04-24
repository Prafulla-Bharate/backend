"""
User Admin Configuration
========================
Django admin configuration for user models.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from apps.users.models import (
    User,
    UserToken,
    UserPreferences,
    EmailVerificationToken,
    PasswordResetToken,
    LoginAttempt,
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin configuration for User model."""
    
    list_display = [
        "email",
        "first_name",
        "last_name",
        "is_active",
        "is_verified",
        "is_staff",
        "created_at",
    ]
    list_filter = [
        "is_active",
        "is_verified",
        "is_staff",
        "is_superuser",
        "experience_level",
        "created_at",
    ]
    search_fields = ["email", "first_name", "last_name"]
    ordering = ["-created_at"]
    
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Personal Info",
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "phone",
                    "location",
                    "bio",
                    "experience_level",
                )
            },
        ),
        (
            "Social Links",
            {
                "fields": (
                    "linkedin_url",
                    "github_url",
                    "portfolio_url",
                )
            },
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_verified",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (
            "Important Dates",
            {
                "fields": (
                    "last_login",
                    "email_verified_at",
                    "created_at",
                    "updated_at",
                    "deleted_at",
                )
            },
        ),
    )
    
    readonly_fields = [
        "created_at",
        "updated_at",
        "last_login",
        "email_verified_at",
    ]
    
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "first_name",
                    "last_name",
                    "password1",
                    "password2",
                ),
            },
        ),
    )


@admin.register(UserPreferences)
class UserPreferencesAdmin(admin.ModelAdmin):
    """Admin configuration for UserPreferences model."""
    
    list_display = [
        "user",
        "theme",
        "language",
        "email_notifications",
        "created_at",
    ]
    list_filter = ["theme", "language", "email_notifications"]
    search_fields = ["user__email"]
    raw_id_fields = ["user"]


@admin.register(UserToken)
class UserTokenAdmin(admin.ModelAdmin):
    """Admin configuration for UserToken model."""
    
    list_display = [
        "user",
        "ip_address",
        "expires_at",
        "revoked_at",
        "created_at",
    ]
    list_filter = ["revoked_at", "created_at"]
    search_fields = ["user__email", "ip_address"]
    raw_id_fields = ["user"]
    readonly_fields = [
        "access_token_hash",
        "refresh_token_hash",
        "created_at",
    ]


@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    """Admin configuration for LoginAttempt model."""
    
    list_display = [
        "email",
        "ip_address",
        "successful",
        "created_at",
    ]
    list_filter = ["successful", "created_at"]
    search_fields = ["email", "ip_address"]
    readonly_fields = ["created_at"]


@admin.register(EmailVerificationToken)
class EmailVerificationTokenAdmin(admin.ModelAdmin):
    """Admin configuration for EmailVerificationToken model."""
    
    list_display = [
        "user",
        "expires_at",
        "used_at",
        "created_at",
    ]
    list_filter = ["used_at", "created_at"]
    search_fields = ["user__email"]
    raw_id_fields = ["user"]


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    """Admin configuration for PasswordResetToken model."""
    
    list_display = [
        "user",
        "ip_address",
        "expires_at",
        "used_at",
        "created_at",
    ]
    list_filter = ["used_at", "created_at"]
    search_fields = ["user__email", "ip_address"]
    raw_id_fields = ["user"]
