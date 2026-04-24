"""
Core Pagination
===============
Custom pagination classes for the CareerAI API.
"""

from collections import OrderedDict
from typing import Any, Dict, List, Optional

from rest_framework.pagination import (
    CursorPagination,
)
from rest_framework.response import Response


class CursorPaginationWithCount(CursorPagination):
    """
    Cursor-based pagination with total count.
    
    Cursor pagination is more efficient for large datasets and prevents
    issues with items being added/removed between page requests.
    """
    
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
    ordering = "-created_at"
    cursor_query_param = "cursor"

    def get_paginated_response(self, data: List[Any]) -> Response:
        """Return paginated response with cursor links — standard DRF shape so
        CareerAIJSONRenderer can wrap it without double-encoding."""
        return Response(
            OrderedDict(
                [
                    ("count", self.get_count_from_cursor()),
                    ("next", self.get_next_link()),
                    ("previous", self.get_previous_link()),
                    ("results", data),
                ]
            )
        )

    def get_count_from_cursor(self) -> Optional[int]:
        """Best-effort total count — may be None if queryset is complex."""
        try:
            return self.page.paginator.count  # type: ignore[attr-defined]
        except Exception:
            return None

    def get_paginated_response_schema(self, schema: Dict) -> Dict:
        """Return schema for paginated response."""
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "data": schema,
                "pagination": {
                    "type": "object",
                    "properties": {
                        "next": {"type": "string", "nullable": True},
                        "previous": {"type": "string", "nullable": True},
                        "page_size": {"type": "integer"},
                    },
                },
            },
        }
