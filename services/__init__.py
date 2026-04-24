"""
CareerAI Services Layer
========================
Centralized services for ML, AI, and external integrations.

This module provides:
- ML services for predictions and analysis
- AI/LLM services for content generation (Gemini Pro)
- External API integrations (Jobs, YouTube, Email, Code Execution, S3)
"""

# Lazy imports to avoid circular dependencies and speed up startup

# ============================================================================
# ML SERVICES
# ============================================================================

def get_career_prediction_model():
    """Get trained ML model for career prediction (India-focused)."""
    from services.ml.career_model_v2 import get_career_prediction_model as _get_model
    return _get_model()


def get_skill_matcher():
    """Get skill matcher ML service."""
    from services.ml.skill_matcher import SkillMatcher
    return SkillMatcher()


def get_learning_recommender():
    """Get learning recommender ML service."""
    from services.ml.learning_recommender import LearningRecommender
    return LearningRecommender()


def get_interview_bank_service():
    """Get Interview Bank service (500+ questions + rubrics)."""
    from services.ml.interview_bank import InterviewQuestionBank
    return InterviewQuestionBank()


def get_job_matcher_ml():
    """Get Job Matcher ML service (TF-IDF + cosine similarity)."""
    from services.ml.job_matcher import JobMatcher
    return JobMatcher()


# ============================================================================
# AI SERVICES (Gemini Pro)
# ============================================================================

def get_gemini_service():
    """Get Gemini AI service."""
    from services.ai.gemini import get_gemini_service as _get_gemini
    return _get_gemini()


def get_career_ai_prompts():
    """Get CareerAI prompts service."""
    from services.ai.prompts import CareerAIPrompts
    return CareerAIPrompts()


def get_interview_coach():
    """Get interview coach AI service."""
    from services.ai.interview_coach import InterviewCoach
    return InterviewCoach()


def get_content_generator():
    """Get content generator AI service."""
    from services.ai.content_generator import ContentGenerator
    return ContentGenerator()


# ============================================================================
# EXTERNAL SERVICES - REMOVED
# ============================================================================
# Removed:
# - YouTube service (not used by frontend)
# - Email/SendGrid service (not used)
# - Code execution service (not used)
# - File storage/S3 service (not used)
# - Job search service (replaced by direct JSearch API calls)


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    # ML Services
    "get_career_prediction_model",
    "get_skill_matcher",
    "get_learning_recommender",
    "get_interview_bank_service",
    "get_job_matcher_ml",
    # AI Services
    "get_gemini_service",
    "get_career_ai_prompts",
    "get_interview_coach",
    "get_content_generator",
]
