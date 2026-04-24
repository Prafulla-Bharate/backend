"""
Core Renderers
==============
Custom response renderers for consistent API response format.
"""

from typing import Any, Dict, Optional

from django.utils import timezone
from rest_framework.renderers import JSONRenderer


class CareerAIJSONRenderer(JSONRenderer):
    """
    Custom JSON renderer that wraps all responses in a consistent format.
    
    Success Response Format:
    {
        "success": true,
        "data": {...},
        "message": "Operation successful",
        "timestamp": "2026-01-15T10:30:00Z",
        "request_id": "uuid"
    }
    
    Error responses are handled by the custom exception handler.
    """

    def render(
        self,
        data: Any,
        accepted_media_type: Optional[str] = None,
        renderer_context: Optional[Dict[str, Any]] = None,
    ) -> bytes:
        """Render data into JSON with consistent format."""
        
        if renderer_context is None:
            renderer_context = {}
        
        response = renderer_context.get("response")
        request = renderer_context.get("request")
        
        # Get request ID
        request_id = getattr(request, "request_id", None) if request else None
        
        # Check if this is an error response (already formatted)
        if data and isinstance(data, dict) and "success" in data:
            # Already formatted (error response or paginated response)
            return super().render(data, accepted_media_type, renderer_context)
        
        # Check if response indicates an error
        if response is not None and response.status_code >= 400:
            # Error response - should be handled by exception handler
            # but in case it's not, wrap it
            if not (isinstance(data, dict) and "error" in data):
                formatted_data = {
                    "success": False,
                    "error": {
                        "code": "ERROR",
                        "message": str(data) if data else "An error occurred",
                    },
                    "timestamp": timezone.now().isoformat(),
                    "request_id": request_id,
                }
                return super().render(formatted_data, accepted_media_type, renderer_context)
            return super().render(data, accepted_media_type, renderer_context)
        
        # Success response - wrap in consistent format
        formatted_data = {
            "success": True,
            "data": data,
            "timestamp": timezone.now().isoformat(),
            "request_id": request_id,
        }
        
        # Add message if present in data
        if isinstance(data, dict) and "message" in data:
            formatted_data["message"] = data.pop("message")
            formatted_data["data"] = data if data else None
        
        return super().render(formatted_data, accepted_media_type, renderer_context)
