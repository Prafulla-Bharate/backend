"""
ML Services Package
===================
Machine Learning services for career prediction, skill matching, and analysis.

NEW SERVICES (LLM-Free Production Systems):
- QuizBankGenerator, QuizSelector: 5000+ pre-built questions (no LLM at runtime)
- InterviewQuestionBank, ResponseEvaluator: 500+ interview questions + STAR rubrics
- JobMatcher: TF-IDF based job matching with cosine similarity
- CareerQuizMapper: Maps 53 career paths to quiz assessments
"""

from services.ml.career_model_v2 import CareerPredictor, get_career_prediction_model, reload_model
from services.ml.skill_matcher import SkillMatcher
from services.ml.learning_recommender import LearningRecommender

# LLM-Free Production Services
from services.ml.interview_bank import InterviewQuestionBank, ResponseEvaluator
from services.ml.job_matcher import JobMatcher


__all__ = [
    # Core ML Services
    "CareerPredictor",
    "get_career_prediction_model",
    "reload_model",
    "SkillMatcher",
    "LearningRecommender",
    # LLM-Free Production Services
    "InterviewQuestionBank",
    "ResponseEvaluator",
    "JobMatcher",
]
