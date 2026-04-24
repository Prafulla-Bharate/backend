"""
Base ML Service Classes
========================
Abstract base classes and interfaces for ML services.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TypeVar, Generic
from datetime import datetime

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class PredictionResult(Generic[T]):
    """
    Standard prediction result container.
    
    Provides a consistent interface for all ML predictions with
    confidence scoring, explanations, and metadata.
    """
    prediction: T
    confidence: float  # 0.0 to 1.0
    explanations: List[str] = field(default_factory=list)
    factors: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    model_version: str = "1.0.0"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "prediction": self.prediction if not hasattr(self.prediction, 'to_dict') 
                          else self.prediction.to_dict(),
            "confidence": round(self.confidence, 4),
            "explanations": self.explanations,
            "factors": {k: round(v, 4) for k, v in self.factors.items()},
            "metadata": self.metadata,
            "model_version": self.model_version,
        }


@dataclass
class CareerMatch:
    """Represents a matched career with scoring details."""
    career_id: str
    title: str
    match_score: float
    skill_match: float
    experience_match: float
    industry_match: float
    growth_potential: float
    salary_range: Dict[str, float]
    reasons: List[str]
    skill_gaps: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "career_id": self.career_id,
            "title": self.title,
            "match_score": round(self.match_score, 3),
            "skill_match": round(self.skill_match, 3),
            "experience_match": round(self.experience_match, 3),
            "industry_match": round(self.industry_match, 3),
            "growth_potential": round(self.growth_potential, 3),
            "salary_range": self.salary_range,
            "reasons": self.reasons,
            "skill_gaps": self.skill_gaps,
        }


@dataclass  
class SkillProfile:
    """User's skill profile for matching."""
    skills: List[str]
    skill_levels: Dict[str, int]  # skill_name -> level (1-5)
    years_experience: float
    education_level: str
    current_role: Optional[str]
    current_industry: Optional[str]
    certifications: List[str] = field(default_factory=list)
    
    @classmethod
    def from_user(cls, user) -> "SkillProfile":
        """Build skill profile from user object."""
        skills = []
        skill_levels = {}
        years_experience = 0.0
        education_level = "unknown"
        current_role = None
        current_industry = None
        certifications = []
        
        # Extract skills
        if hasattr(user, 'skills'):
            for user_skill in user.skills.select_related('skill').all():
                skills.append(user_skill.skill.name.lower())
                skill_levels[user_skill.skill.name.lower()] = user_skill.proficiency_level or 3
        
        # Extract experience
        if hasattr(user, 'experiences'):
            experiences = user.experiences.all()
            total_months = 0
            for exp in experiences:
                if exp.start_date:
                    from django.utils import timezone
                    end = exp.end_date or timezone.now().date()
                    months = (end - exp.start_date).days // 30
                    total_months += max(0, months)
                
                if exp.is_current:
                    current_role = exp.job_title
                    current_industry = exp.company_industry
            
            years_experience = round(total_months / 12, 1)
        
        # Extract education
        if hasattr(user, 'educations'):
            edu = user.educations.order_by('-end_date').first()
            if edu:
                education_level = edu.degree_type or "unknown"
        
        # Extract certifications
        if hasattr(user, 'certifications'):
            certifications = list(
                user.certifications.values_list('name', flat=True)
            )
        
        return cls(
            skills=skills,
            skill_levels=skill_levels,
            years_experience=years_experience,
            education_level=education_level,
            current_role=current_role,
            current_industry=current_industry,
            certifications=certifications,
        )


class BasePredictor(ABC):
    """
    Abstract base class for all ML predictors.
    
    Provides common interface and utilities for prediction services.
    """
    
    def __init__(self):
        self.model_name = self.__class__.__name__
        self.model_version = "1.0.0"
        self._is_loaded = False
        logger.info(f"Initializing {self.model_name}")
    
    @abstractmethod
    def predict(self, *args, **kwargs) -> PredictionResult:
        """Make a prediction. Must be implemented by subclasses."""
        pass
    
    def validate_input(self, data: Dict[str, Any]) -> bool:
        """Validate input data before prediction."""
        return True
    
    def preprocess(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Preprocess input data before prediction."""
        return data
    
    def postprocess(self, result: Any) -> Any:
        """Postprocess prediction result."""
        return result
    
    def get_model_info(self) -> Dict[str, Any]:
        """Return model metadata."""
        return {
            "name": self.model_name,
            "version": self.model_version,
            "is_loaded": self._is_loaded,
        }


class BaseMatcher(ABC):
    """
    Abstract base class for matching/similarity services.
    """
    
    @abstractmethod
    def compute_similarity(self, source: Any, target: Any) -> float:
        """Compute similarity score between source and target."""
        pass
    
    @abstractmethod
    def find_matches(self, source: Any, candidates: List[Any], top_k: int = 10) -> List[Any]:
        """Find top-k matches for source from candidates."""
        pass
