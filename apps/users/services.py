"""
User Services
=============
Business logic services for user management.
"""

import logging
from typing import Optional

from django.conf import settings
from django.core.mail import send_mail

from apps.users.models import (
    User,
    EmailVerificationToken,
    PasswordResetToken,
)

logger = logging.getLogger(__name__)


class AuthService:
    """
    Authentication service for user management.
    
    Handles:
    - Email verification
    - Password reset
    - Account management
    """

    @staticmethod
    def send_verification_email(user: User) -> None:
        """
        Send email verification link to user.
        
        Args:
            user: The user to send verification email to.
        """
        # Create verification token
        token = EmailVerificationToken.create_for_user(
            user,
            hours_valid=settings.EMAIL_VERIFICATION_TOKEN_EXPIRY_HOURS,
        )
        
        # Build verification URL
        verification_url = f"{settings.FRONTEND_URL}/verify-email?token={token.token}"
        
        # Send email (in production, use Celery task)
        try:
            subject = "Verify your CareerPilot account"
            message = f"""
Hello {user.first_name or 'there'},

Thank you for registering with CareerPilot!

Please click the link below to verify your email address:
{verification_url}

This link will expire in {settings.EMAIL_VERIFICATION_TOKEN_EXPIRY_HOURS} hours.

If you didn't create an account, please ignore this email.

Best regards,
The CareerPilot Team
            """
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
            
            logger.info(f"Verification email sent to: {user.email}")
            
        except Exception as e:
            logger.error(f"Failed to send verification email to {user.email}: {e}")

    @staticmethod
    def send_password_reset_email(
        user: User,
        ip_address: Optional[str] = None,
    ) -> None:
        """
        Send password reset link to user.
        
        Args:
            user: The user to send reset email to.
            ip_address: IP address of the request (for logging).
        """
        # Create reset token
        token = PasswordResetToken.create_for_user(
            user,
            hours_valid=settings.PASSWORD_RESET_TOKEN_EXPIRY_HOURS,
            ip_address=ip_address,
        )
        
        # Build reset URL
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token.token}"
        
        # Send email
        try:
            subject = "Reset your CareerPilot password"
            message = f"""
Hello {user.first_name or 'there'},

We received a request to reset your password.

Please click the link below to reset your password:
{reset_url}

This link will expire in {settings.PASSWORD_RESET_TOKEN_EXPIRY_HOURS} hours.

If you didn't request a password reset, please ignore this email.
Your password will remain unchanged.

Best regards,
The CareerPilot Team
            """
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
            
            logger.info(f"Password reset email sent to: {user.email}")
            
        except Exception as e:
            logger.error(f"Failed to send password reset email to {user.email}: {e}")

