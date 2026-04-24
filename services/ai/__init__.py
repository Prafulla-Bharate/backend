"""
AI Services Package
===================
AI/LLM services using Gemini Pro as primary provider.
Includes content generation, interview coaching, career prompts, and more.
"""

from services.ai.base import AIService, AIProvider
from services.ai.gemini import GeminiAIService, get_gemini_service
from services.ai.prompts import CareerAIPrompts, AIPromptsService, get_career_ai_prompts
from services.ai.interview_coach import InterviewCoach
from services.ai.content_generator import ContentGenerator

__all__ = [
    "AIService",
    "AIProvider",
    "GeminiAIService",
    "get_gemini_service",
    "CareerAIPrompts",
    "AIPromptsService",  # Alias for CareerAIPrompts
    "get_career_ai_prompts",
    "InterviewCoach",
    "ContentGenerator",
]
