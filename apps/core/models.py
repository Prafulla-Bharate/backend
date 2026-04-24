"""
Core Base Models
================
Abstract base models providing common functionality across all apps.
"""

import uuid
from typing import Optional

from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    """
    Abstract base model providing created_at and updated_at timestamps.
    
    All models should inherit from this to track creation and modification times.
    """
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="Timestamp when the record was created",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when the record was last updated",
    )

    class Meta:
        abstract = True
        ordering = ["-created_at"]


class UUIDModel(models.Model):
    """
    Abstract base model using UUID as primary key.
    
    Provides better security and scalability than auto-incrementing integers.
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier",
    )

    class Meta:
        abstract = True


class SoftDeleteModel(models.Model):
    """
    Abstract base model providing soft delete functionality.
    
    Records are not actually deleted from the database, but marked as deleted.
    """
    
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Timestamp when the record was soft deleted",
    )

    class Meta:
        abstract = True

    @property
    def is_deleted(self) -> bool:
        """Check if the record is soft deleted."""
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        """Mark the record as deleted without removing from database."""
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at", "updated_at"])

    def restore(self) -> None:
        """Restore a soft-deleted record."""
        self.deleted_at = None
        self.save(update_fields=["deleted_at", "updated_at"])

    def hard_delete(self) -> None:
        """Permanently delete the record from the database."""
        super().delete()


class SoftDeleteManager(models.Manager):
    """Manager that excludes soft-deleted records by default."""
    
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)

    def with_deleted(self):
        """Include soft-deleted records in the queryset."""
        return super().get_queryset()

    def only_deleted(self):
        """Return only soft-deleted records."""
        return super().get_queryset().filter(deleted_at__isnull=False)


class BaseModel(UUIDModel, TimeStampedModel, SoftDeleteModel):
    """
    Complete base model combining UUID, timestamps, and soft delete.
    
    This is the recommended base model for most CareerAI models.
    """
    
    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True


class AuditLog(UUIDModel, TimeStampedModel):
    """
    Audit log model for tracking user actions.
    
    Records all significant actions for security and debugging purposes.
    """
    
    user_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="ID of the user who performed the action",
    )
    action = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Type of action performed",
    )
    resource_type = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        db_index=True,
        help_text="Type of resource affected",
    )
    resource_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="ID of the resource affected",
    )
    changes = models.JSONField(
        null=True,
        blank=True,
        help_text="JSON object containing the changes made",
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address of the request",
    )
    user_agent = models.TextField(
        null=True,
        blank=True,
        help_text="User agent string of the request",
    )

    class Meta:
        db_table = "audit_log"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user_id", "created_at"]),
            models.Index(fields=["action", "created_at"]),
            models.Index(fields=["resource_type", "resource_id"]),
        ]

    def __str__(self) -> str:
        return f"{self.action} by {self.user_id} at {self.created_at}"


class APIUsageLog(UUIDModel, TimeStampedModel):
    """
    API usage log for rate limiting and analytics.
    
    Tracks API endpoint usage for monitoring and rate limiting.
    """
    
    user_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
    )
    endpoint = models.CharField(max_length=500)
    method = models.CharField(max_length=10)
    status_code = models.IntegerField()
    response_time_ms = models.IntegerField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        db_table = "api_usage_log"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user_id", "created_at"]),
            models.Index(fields=["endpoint", "created_at"]),
        ]


class FeatureFlag(UUIDModel, TimeStampedModel):
    """
    Feature flag model for gradual rollouts and A/B testing.
    """
    
    name = models.CharField(max_length=255, unique=True, db_index=True)
    description = models.TextField(null=True, blank=True)
    is_enabled = models.BooleanField(default=False)
    rollout_percentage = models.IntegerField(
        default=0,
        help_text="Percentage of users (0-100) to enable for",
    )

    class Meta:
        db_table = "feature_flags"

    def __str__(self) -> str:
        return f"{self.name} ({'enabled' if self.is_enabled else 'disabled'})"

    def is_enabled_for_user(self, user_id: Optional[uuid.UUID]) -> bool:
        """
        Check if the feature is enabled for a specific user.
        
        Uses consistent hashing based on user ID for gradual rollouts.
        """
        if not self.is_enabled:
            return False
        
        if self.rollout_percentage >= 100:
            return True
        
        if self.rollout_percentage <= 0:
            return False
        
        if user_id is None:
            return False
        
        # Consistent hash for gradual rollout
        user_hash = hash(str(user_id)) % 100
        return user_hash < self.rollout_percentage
