"""
Core Exception Handling
=======================
Custom exception handler and exception classes for consistent error responses.
"""

import logging
from typing import Any, Dict, Optional

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import APIException, AuthenticationFailed
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


# =============================================================================
# CUSTOM EXCEPTION CLASSES
# =============================================================================

class CareerAIException(APIException):
    """Base exception class for CareerAI API."""
    
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "An error occurred."
    default_code = "error"

    def __init__(
        self,
        detail: Optional[str] = None,
        code: Optional[str] = None,
        status_code: Optional[int] = None,
    ):
        if detail is not None:
            self.detail = detail
        else:
            self.detail = self.default_detail
        
        if code is not None:
            self.code = code
        else:
            self.code = self.default_code
        
        if status_code is not None:
            self.status_code = status_code


class ValidationException(CareerAIException):
    """Exception for validation errors."""
    
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Validation failed."
    default_code = "VALIDATION_ERROR"


class ResourceNotFoundException(CareerAIException):
    """Exception when a requested resource is not found."""
    
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Resource not found."
    default_code = "NOT_FOUND"


class ResourceExistsException(CareerAIException):
    """Exception when a resource already exists."""
    
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Resource already exists."
    default_code = "CONFLICT"


class UnauthorizedException(CareerAIException):
    """Exception for authentication failures."""
    
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = "Authentication required."
    default_code = "UNAUTHORIZED"


class ForbiddenException(CareerAIException):
    """Exception for permission denied errors."""
    
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "Permission denied."
    default_code = "FORBIDDEN"


class AccountLockedException(CareerAIException):
    """Exception when account is locked due to failed login attempts."""
    
    status_code = status.HTTP_423_LOCKED
    default_detail = "Account temporarily locked due to too many failed login attempts."
    default_code = "ACCOUNT_LOCKED"


# =============================================================================
# CUSTOM EXCEPTION HANDLER
# =============================================================================

def custom_exception_handler(exc: Exception, context: Dict[str, Any]) -> Response:
    """
    Custom exception handler for consistent error response format.
    
    All error responses follow this format:
    {
        "success": false,
        "error": {
            "code": "ERROR_CODE",
            "message": "Human-readable message",
            "details": {...}  // Optional, for validation errors
        },
        "timestamp": "2026-01-15T10:30:00Z",
        "request_id": "uuid"
    }
    """
    # Get request ID from context
    request = context.get("request")
    request_id = getattr(request, "request_id", None) if request else None
    
    # Handle Django exceptions
    if isinstance(exc, Http404):
        exc = ResourceNotFoundException()
    elif isinstance(exc, PermissionDenied):
        exc = ForbiddenException()
    elif isinstance(exc, ValidationError):
        exc = ValidationException(detail=str(exc))
    
    # Call REST framework's default exception handler
    response = exception_handler(exc, context)
    
    if response is not None:
        # Build custom error response
        error_response = _build_error_response(exc, response, request_id)
        response.data = error_response
        
        # Log error
        _log_exception(exc, context, response.status_code)
        
        return response
    
    # Handle unexpected exceptions
    logger.exception("Unhandled exception", extra={"request_id": request_id})
    
    if settings.DEBUG:
        error_detail = str(exc)
    else:
        error_detail = "An unexpected error occurred."
    
    return Response(
        {
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": error_detail,
            },
            "timestamp": timezone.now().isoformat(),
            "request_id": request_id,
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def _build_error_response(
    exc: Exception,
    response: Response,
    request_id: Optional[str],
) -> Dict[str, Any]:
    """Build standardized error response."""
    
    # Determine error code
    if hasattr(exc, "code"):
        error_code = exc.code
    elif hasattr(exc, "default_code"):
        error_code = exc.default_code
    else:
        error_code = "ERROR"
    
    # Determine error message
    if hasattr(exc, "detail"):
        if isinstance(exc.detail, dict):
            # Validation errors with field details
            error_message = "Validation failed."
            error_details = exc.detail
        elif isinstance(exc.detail, list):
            error_message = exc.detail[0] if exc.detail else "An error occurred."
            error_details = None
        else:
            error_message = str(exc.detail)
            error_details = None
    else:
        error_message = str(exc)
        error_details = None
    
    error_response = {
        "success": False,
        "error": {
            "code": error_code,
            "message": error_message,
        },
        "timestamp": timezone.now().isoformat(),
        "request_id": request_id,
    }
    
    if error_details:
        error_response["error"]["details"] = error_details
    
    return error_response


def _log_exception(exc: Exception, context: Dict[str, Any], status_code: int) -> None:
    """Log exception with appropriate level."""
    request = context.get("request")
    request_id = getattr(request, "request_id", None) if request else None
    
    log_data = {
        "request_id": request_id,
        "exception_type": type(exc).__name__,
        "status_code": status_code,
    }
    
    if request:
        log_data["path"] = request.path
        log_data["method"] = request.method
        if hasattr(request, "user") and request.user.is_authenticated:
            log_data["user_id"] = str(request.user.id)
    
    if status_code >= 500:
        logger.error("Server error", extra=log_data, exc_info=exc)
    elif status_code >= 400:
        logger.warning("Client error", extra=log_data)
