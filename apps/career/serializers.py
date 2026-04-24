# Utility to transform prediction to frontend-friendly format
from django.utils import timezone

def transform_prediction_for_frontend(prediction):
    """
    Returns a dict with keys:
      - prediction_id (UUID str)
      - status (str)
      - primary_career (object)
      - alternative_careers (list)
      - skill_analysis (object)
      - source (str)
      - timestamp (iso8601)
    """
    import logging
    logger = logging.getLogger(__name__)
    # Pick the best match as primary
    careers = prediction.recommended_careers or []
    primary = careers[0] if careers else None
    alternatives = careers[1:] if len(careers) > 1 else []

    def _normalise_confidence(raw):
        """Ensure confidence is always 0.0-1.0.
        Gemini sometimes returns 0-100 scale despite instructions."""
        try:
            v = float(raw)
        except (TypeError, ValueError):
            return 0.0
        return v / 100.0 if v > 1.0 else v

    def map_career(c):
        salary = c.get("salary_range", {})
        if not isinstance(salary, dict):
            salary = {}
        sal_min = float(salary.get("min", 0) or 0)
        sal_max = float(salary.get("max", 0) or 0)
        # Friendly formatted salary string (INR lakhs/crores)
        def fmt_inr(amount):
            if amount >= 10_00_000:
                return f"₹{amount/10_00_000:.1f}Cr"
            elif amount >= 1_00_000:
                return f"₹{amount/1_00_000:.1f}L"
            return f"₹{int(amount):,}"
        salary_str = f"{fmt_inr(sal_min)} - {fmt_inr(sal_max)}" if sal_min or sal_max else ""
        return {
            "title": c.get("title", ""),
            "confidence": _normalise_confidence(c.get("match_score", 0)),
            "description": ", ".join(c.get("reasons", [])) if isinstance(c.get("reasons"), list) else c.get("reasoning", ""),
            "demand_level": c.get("market_demand", ""),
            "salary_range": salary,
            "salary_range_str": salary_str,
            "growth_rate": c.get("growth_potential", c.get("growth_rate", "")),
            "trends": c.get("trends", {}),
            "skills_matched": c.get("skills_matched", []),
            "skills_to_develop": c.get("skills_to_develop", []),
            "source": c.get("source", prediction.model_used),
            "job_openings": int(c.get("job_openings", 0) or 0),
            "avg_salary": int(sal_max or sal_min),
            # Pass through new rich fields so frontend card stats always have real data
            "demand_trend": c.get("demand_trend", "rising"),
            "industry_growth": c.get("industry_growth", 0),
            "top_companies": c.get("top_companies", []),
            "top_locations": c.get("top_locations", []),
            "success_factors": c.get("success_factors", []),
            "challenges": c.get("challenges", []),
            "day_in_life": c.get("day_in_life", ""),
        }

    # --- Skill analysis: correct field mapping ---
    # prediction.skill_gaps  = critical GAPs (list of missing skills)
    # prediction.recommended_skills = ordered learning list
    # skills_matched comes from the top recommended career
    primary_skills_matched = primary.get("skills_matched", []) if primary else []

    result = {
        "prediction_id": str(prediction.id),
        "status": prediction.status,
        "is_accepted": prediction.is_accepted,
        "accepted_career_title": prediction.accepted_career_title or "",
        "primary_career": map_career(primary) if primary else None,
        "alternative_careers": [map_career(c) for c in alternatives],
        "skill_analysis": {
            "matching_skills": primary_skills_matched,
            "skill_gaps": prediction.skill_gaps or [],
            "recommended_learning_order": prediction.recommended_skills or [],
        },
        "source": prediction.model_used,
        "timestamp": prediction.updated_at.isoformat() if hasattr(prediction, "updated_at") else timezone.now().isoformat(),
    }
    # Use ascii() to safely log non-ASCII chars (e.g. ₹) on Windows cp1252 consoles
    logger.info("[Prediction] transform_prediction_for_frontend output: %s", ascii(result))
    return result
"""
Career Serializers
==================
Serializers for career-related data.
"""

from rest_framework import serializers

from apps.career.models import (
    CareerPrediction,
    CareerPath,
)


# ============================================================================
# Career Prediction Serializers
# ============================================================================

class CareerPredictionSerializer(serializers.ModelSerializer):
    """Serializer for career predictions."""
    
    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True
    )
    
    class Meta:
        model = CareerPrediction
        fields = [
            "id",
            "status",
            "status_display",
            "error_message",
            "recommended_careers",
            "current_career_assessment",
            "skill_gaps",
            "recommended_skills",
            "recommended_courses",
            "career_timeline",
            "salary_projection",
            "confidence_score",
            "model_used",
            "processing_time_ms",
            "user_rating",
            "user_feedback",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "error_message",
            "recommended_careers",
            "current_career_assessment",
            "skill_gaps",
            "recommended_skills",
            "recommended_courses",
            "career_timeline",
            "salary_projection",
            "confidence_score",
            "model_used",
            "processing_time_ms",
            "created_at",
        ]


class CareerPredictionRequestSerializer(serializers.Serializer):
    """Serializer for requesting career prediction."""
    
    target_industries = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="Target industries to focus on"
    )
    target_roles = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="Target roles to focus on"
    )
    career_level = serializers.ChoiceField(
        choices=CareerPath.CareerLevel.choices,
        required=False,
        help_text="Target career level"
    )
    location_preference = serializers.CharField(
        required=False,
        help_text="Preferred location/region"
    )
    salary_expectation = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        help_text="Expected salary"
    )
    timeline_years = serializers.IntegerField(
        min_value=1,
        max_value=20,
        default=5,
        help_text="Planning timeline in years"
    )
