"""
Core Middleware
===============
Custom middleware for request logging, rate limiting, and audit logging.
"""

import json
import logging
import time
import uuid
from typing import Any, Callable, Optional

from django.conf import settings
from django.core.cache import cache
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils import timezone
from rest_framework import status

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware:
    """
    Middleware for logging all incoming requests.
    
    Adds request ID for tracing and logs request/response details.
    """

    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        request.request_id = request_id
        
        # Record start time
        start_time = time.time()
        
        # Process request
        response = self.get_response(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Add headers to response
        response["X-Request-ID"] = request_id
        response["X-Response-Time"] = f"{duration:.3f}s"
        
        # Log request details
        logger.info(
            "Request completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.path,
                "status_code": response.status_code,
                "duration": duration,
                "user_id": getattr(request.user, "id", None),
                "ip": self.get_client_ip(request),
            },
        )
        
        return response

    @staticmethod
    def get_client_ip(request: HttpRequest) -> str:
        """Extract client IP from request headers."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")


class RateLimitMiddleware:
    """
    Middleware for rate limiting API requests.
    
    Implements token bucket algorithm with Redis caching.
    """

    def __init__(self, get_response: Callable):
        self.get_response = get_response
        self.requests_per_minute = getattr(
            settings, "RATE_LIMIT_REQUESTS_PER_MINUTE", 100
        )
        self.burst_limit = getattr(settings, "RATE_LIMIT_BURST", 150)

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Skip rate limiting for certain paths
        if self._should_skip(request):
            return self.get_response(request)
        
        # Get rate limit key
        key = self._get_rate_limit_key(request)
        
        # Check rate limit
        is_allowed, remaining, reset_time = self._check_rate_limit(key)
        
        if not is_allowed:
            return JsonResponse(
                {
                    "success": False,
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "Too many requests. Please try again later.",
                    },
                    "timestamp": timezone.now().isoformat(),
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
                headers={
                    "X-RateLimit-Limit": str(self.requests_per_minute),
                    "X-RateLimit-Remaining": str(remaining),
                    "X-RateLimit-Reset": str(reset_time),
                    "Retry-After": str(reset_time),
                },
            )
        
        # Process request and add rate limit headers
        response = self.get_response(request)
        response["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response["X-RateLimit-Remaining"] = str(remaining)
        
        return response

    def _should_skip(self, request: HttpRequest) -> bool:
        """Check if request should skip rate limiting."""
        skip_paths = ["/health/", "/admin/", "/static/", "/media/"]
        return any(request.path.startswith(path) for path in skip_paths)

    def _get_rate_limit_key(self, request: HttpRequest) -> str:
        """Generate rate limit key based on user or IP."""
        if hasattr(request, "user") and request.user.is_authenticated:
            return f"ratelimit:user:{request.user.id}"
        
        ip = RequestLoggingMiddleware.get_client_ip(request)
        return f"ratelimit:ip:{ip}"

    def _check_rate_limit(self, key: str) -> tuple[bool, int, int]:
        """
        Check if request is within rate limit.
        
        Returns: (is_allowed, remaining_requests, reset_time_seconds)
        """
        try:
            current_count = cache.get(key, 0)
            
            if current_count >= self.requests_per_minute:
                ttl = cache.ttl(key) if hasattr(cache, "ttl") else 60
                return False, 0, ttl
            
            # Increment counter
            if current_count == 0:
                cache.set(key, 1, timeout=60)
            else:
                cache.incr(key)
            
            remaining = self.requests_per_minute - current_count - 1
            return True, max(remaining, 0), 0
            
        except Exception as e:
            logger.warning(f"Rate limiting error: {e}")
            # Fail open - allow request if cache fails
            return True, self.requests_per_minute, 0


class AuditLogMiddleware:
    """
    Middleware for audit logging of user actions.
    
    Logs all state-changing requests (POST, PUT, PATCH, DELETE).
    """

    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Only audit state-changing methods
        if request.method not in ["POST", "PUT", "PATCH", "DELETE"]:
            return self.get_response(request)
        
        # Skip certain paths
        if self._should_skip(request):
            return self.get_response(request)
        
        response = self.get_response(request)
        
        # Log if successful
        if 200 <= response.status_code < 300:
            self._log_action(request, response)
        
        return response

    def _should_skip(self, request: HttpRequest) -> bool:
        """Check if request should skip audit logging."""
        skip_paths = ["/admin/", "/static/", "/media/", "/health/"]
        return any(request.path.startswith(path) for path in skip_paths)

    def _log_action(self, request: HttpRequest, response: HttpResponse) -> None:
        """Log the action to audit log."""
        from apps.core.models import AuditLog
        
        try:
            user_id = None
            if hasattr(request, "user") and request.user.is_authenticated:
                user_id = request.user.id
            
            # Determine action from request
            action = self._get_action_name(request)
            
            # Get request body (sanitized)
            changes = self._get_sanitized_body(request)
            
            AuditLog.objects.create(
                user_id=user_id,
                action=action,
                resource_type=self._get_resource_type(request.path),
                ip_address=RequestLoggingMiddleware.get_client_ip(request),
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
                changes=changes,
            )
        except Exception as e:
            logger.error(f"Audit logging error: {e}")

    def _get_action_name(self, request: HttpRequest) -> str:
        """Generate action name from request."""
        method_map = {
            "POST": "create",
            "PUT": "update",
            "PATCH": "partial_update",
            "DELETE": "delete",
        }
        action = method_map.get(request.method, request.method.lower())
        path_parts = request.path.strip("/").split("/")
        resource = path_parts[-1] if path_parts else "unknown"
        return f"{action}_{resource}"

    def _get_resource_type(self, path: str) -> str:
        """Extract resource type from path."""
        parts = path.strip("/").split("/")
        if len(parts) >= 2:
            return parts[1]  # e.g., /api/users/ -> users
        return parts[0] if parts else "unknown"

    def _get_sanitized_body(self, request: HttpRequest) -> Optional[dict]:
        """Get sanitized request body, removing sensitive fields."""
        sensitive_fields = ["password", "token", "secret", "key", "credit_card"]
        
        try:
            if request.content_type == "application/json":
                body = json.loads(request.body)
                if isinstance(body, dict):
                    return {
                        k: "[REDACTED]" if any(s in k.lower() for s in sensitive_fields) else v
                        for k, v in body.items()
                    }
            return None
        except Exception:
            return None
