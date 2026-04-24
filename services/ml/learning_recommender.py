"""
Learning Recommender Service
============================
ML-based learning path recommendation engine.

Features:
1. Skill gap-based course recommendations
2. Personalized learning paths
3. Time estimation for skill acquisition
4. Priority-based learning order
5. Multiple learning resource types
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from services.ml.base import BasePredictor, PredictionResult, SkillProfile
from services.ml.skill_matcher import get_skill_matcher, SKILL_TAXONOMY

logger = logging.getLogger(__name__)


# Learning resources database (simulated)
LEARNING_RESOURCES = {
    "python": [
        {"title": "Python for Everybody", "provider": "Coursera", "type": "course", "duration_hours": 40, "level": "beginner", "rating": 4.8, "url": "https://coursera.org/python"},
        {"title": "Automate the Boring Stuff", "provider": "Udemy", "type": "course", "duration_hours": 10, "level": "beginner", "rating": 4.7, "url": "https://udemy.com/automate"},
        {"title": "Python Crash Course", "provider": "Book", "type": "book", "duration_hours": 20, "level": "beginner", "rating": 4.6},
        {"title": "Real Python Tutorials", "provider": "Real Python", "type": "tutorial", "duration_hours": 15, "level": "intermediate", "rating": 4.7, "url": "https://realpython.com"},
    ],
    "javascript": [
        {"title": "JavaScript: The Complete Guide", "provider": "Udemy", "type": "course", "duration_hours": 50, "level": "beginner", "rating": 4.7},
        {"title": "freeCodeCamp JavaScript", "provider": "freeCodeCamp", "type": "course", "duration_hours": 30, "level": "beginner", "rating": 4.8, "url": "https://freecodecamp.org"},
        {"title": "Eloquent JavaScript", "provider": "Book", "type": "book", "duration_hours": 25, "level": "intermediate", "rating": 4.5},
    ],
    "react": [
        {"title": "React - The Complete Guide", "provider": "Udemy", "type": "course", "duration_hours": 48, "level": "intermediate", "rating": 4.8},
        {"title": "React Official Tutorial", "provider": "React", "type": "tutorial", "duration_hours": 8, "level": "beginner", "rating": 4.6, "url": "https://react.dev/learn"},
        {"title": "Epic React", "provider": "Kent C. Dodds", "type": "workshop", "duration_hours": 20, "level": "advanced", "rating": 4.9},
    ],
    "aws": [
        {"title": "AWS Certified Solutions Architect", "provider": "A Cloud Guru", "type": "course", "duration_hours": 40, "level": "intermediate", "rating": 4.7},
        {"title": "AWS Fundamentals", "provider": "Coursera", "type": "course", "duration_hours": 20, "level": "beginner", "rating": 4.5},
        {"title": "AWS Training", "provider": "AWS", "type": "official", "duration_hours": 30, "level": "beginner", "rating": 4.6, "url": "https://aws.amazon.com/training"},
    ],
    "machine learning": [
        {"title": "Machine Learning by Andrew Ng", "provider": "Coursera", "type": "course", "duration_hours": 60, "level": "intermediate", "rating": 4.9, "url": "https://coursera.org/ml"},
        {"title": "Fast.ai Practical Deep Learning", "provider": "Fast.ai", "type": "course", "duration_hours": 40, "level": "intermediate", "rating": 4.8, "url": "https://fast.ai"},
        {"title": "Hands-On Machine Learning", "provider": "Book", "type": "book", "duration_hours": 50, "level": "intermediate", "rating": 4.7},
    ],
    "docker": [
        {"title": "Docker Mastery", "provider": "Udemy", "type": "course", "duration_hours": 20, "level": "beginner", "rating": 4.7},
        {"title": "Docker Deep Dive", "provider": "Pluralsight", "type": "course", "duration_hours": 15, "level": "intermediate", "rating": 4.6},
        {"title": "Docker Official Getting Started", "provider": "Docker", "type": "tutorial", "duration_hours": 5, "level": "beginner", "rating": 4.5, "url": "https://docs.docker.com/get-started"},
    ],
    "kubernetes": [
        {"title": "Kubernetes for Developers", "provider": "Udemy", "type": "course", "duration_hours": 30, "level": "intermediate", "rating": 4.6},
        {"title": "CKAD Certification Course", "provider": "Linux Foundation", "type": "certification", "duration_hours": 40, "level": "advanced", "rating": 4.7},
        {"title": "Kubernetes the Hard Way", "provider": "GitHub", "type": "tutorial", "duration_hours": 20, "level": "advanced", "rating": 4.8},
    ],
    "sql": [
        {"title": "SQL for Data Science", "provider": "Coursera", "type": "course", "duration_hours": 20, "level": "beginner", "rating": 4.6},
        {"title": "SQLZoo Interactive Tutorial", "provider": "SQLZoo", "type": "tutorial", "duration_hours": 10, "level": "beginner", "rating": 4.5, "url": "https://sqlzoo.net"},
        {"title": "Mode SQL Tutorial", "provider": "Mode", "type": "tutorial", "duration_hours": 15, "level": "intermediate", "rating": 4.7},
    ],
    "deep learning": [
        {"title": "Deep Learning Specialization", "provider": "Coursera", "type": "course", "duration_hours": 80, "level": "advanced", "rating": 4.9},
        {"title": "PyTorch for Deep Learning", "provider": "Udemy", "type": "course", "duration_hours": 25, "level": "intermediate", "rating": 4.7},
        {"title": "Deep Learning with Python", "provider": "Book", "type": "book", "duration_hours": 40, "level": "intermediate", "rating": 4.6},
    ],
    "system design": [
        {"title": "Grokking System Design", "provider": "Educative", "type": "course", "duration_hours": 30, "level": "advanced", "rating": 4.8},
        {"title": "Designing Data-Intensive Applications", "provider": "Book", "type": "book", "duration_hours": 50, "level": "advanced", "rating": 4.9},
        {"title": "System Design Primer", "provider": "GitHub", "type": "resource", "duration_hours": 20, "level": "intermediate", "rating": 4.7, "url": "https://github.com/donnemartin/system-design-primer"},
    ],
    "leadership": [
        {"title": "The Manager's Path", "provider": "Book", "type": "book", "duration_hours": 15, "level": "intermediate", "rating": 4.8},
        {"title": "Leadership Skills for Tech", "provider": "Pluralsight", "type": "course", "duration_hours": 10, "level": "intermediate", "rating": 4.5},
    ],
}

# Learning path templates
LEARNING_PATH_TEMPLATES = {
    "frontend_developer": {
        "name": "Frontend Developer Path",
        "description": "Become a proficient frontend developer",
        "skills": ["html", "css", "javascript", "react", "typescript"],
        "duration_weeks": 16,
    },
    "backend_developer": {
        "name": "Backend Developer Path",
        "description": "Master backend development",
        "skills": ["python", "sql", "rest api", "docker", "aws"],
        "duration_weeks": 20,
    },
    "data_scientist": {
        "name": "Data Scientist Path",
        "description": "Become a data scientist",
        "skills": ["python", "sql", "statistics", "machine learning", "deep learning"],
        "duration_weeks": 24,
    },
    "devops_engineer": {
        "name": "DevOps Engineer Path",
        "description": "Master DevOps practices",
        "skills": ["linux", "docker", "kubernetes", "aws", "terraform", "ci/cd"],
        "duration_weeks": 20,
    },
    "ml_engineer": {
        "name": "ML Engineer Path",
        "description": "Become a machine learning engineer",
        "skills": ["python", "machine learning", "deep learning", "docker", "mlops"],
        "duration_weeks": 28,
    },
}


@dataclass
class LearningResource:
    """A learning resource recommendation."""
    skill: str
    title: str
    provider: str
    resource_type: str
    duration_hours: int
    level: str
    rating: float
    url: Optional[str] = None
    priority: str = "medium"  # high, medium, low
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill": self.skill,
            "title": self.title,
            "provider": self.provider,
            "type": self.resource_type,
            "duration_hours": self.duration_hours,
            "level": self.level,
            "rating": self.rating,
            "url": self.url,
            "priority": self.priority,
        }


@dataclass
class LearningPath:
    """A personalized learning path."""
    name: str
    description: str
    target_role: str
    skills_to_learn: List[str]
    resources: List[LearningResource]
    total_duration_hours: int
    estimated_weeks: int
    milestones: List[Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "target_role": self.target_role,
            "skills_to_learn": self.skills_to_learn,
            "resources": [r.to_dict() for r in self.resources],
            "total_duration_hours": self.total_duration_hours,
            "estimated_weeks": self.estimated_weeks,
            "milestones": self.milestones,
        }


class LearningRecommender(BasePredictor):
    """
    Learning path recommendation engine.
    
    Algorithm:
    1. Analyze skill gaps between current and target
    2. Determine learning priority based on career impact
    3. Match skills to learning resources
    4. Optimize learning order (prerequisites first)
    5. Estimate time to completion
    """
    
    def __init__(self):
        super().__init__()
        self.model_version = "2.0.0"
        self.skill_matcher = get_skill_matcher()
        self._is_loaded = True
    
    def predict(
        self,
        profile: SkillProfile = None,
        current_skills: List[str] = None,
        target_role: str = None,
        target_skills: List[str] = None,
        weekly_hours: int = 10,
        preferred_types: List[str] = None,
    ) -> PredictionResult[LearningPath]:
        """
        Generate a personalized learning path.
        
        Args:
            profile: User's skill profile
            current_skills: Current skills (alternative to profile)
            target_role: Target career role
            target_skills: Specific skills to learn
            weekly_hours: Hours available per week for learning
            preferred_types: Preferred resource types (course, book, etc.)
        """
        logger.info(f"Generating learning path for target: {target_role or 'custom'}")
        
        # Get current skills
        if profile:
            current = set(s.lower() for s in profile.skills)
        elif current_skills:
            current = set(s.lower() for s in current_skills)
        else:
            current = set()
        
        # Determine target skills
        if target_skills:
            target = set(s.lower() for s in target_skills)
        elif target_role:
            target = self._get_role_skills(target_role)
        else:
            target = set()
        
        # Calculate skill gaps
        skill_gaps = list(target - current)
        
        # Prioritize skills
        prioritized = self._prioritize_skills(skill_gaps, target_role)
        
        # Get resources for each skill
        resources = []
        for skill, priority in prioritized:
            skill_resources = self._get_resources_for_skill(
                skill, 
                priority,
                preferred_types
            )
            resources.extend(skill_resources)
        
        # Calculate totals
        total_hours = sum(r.duration_hours for r in resources)
        estimated_weeks = max(1, total_hours // weekly_hours)
        
        # Generate milestones
        milestones = self._generate_milestones(prioritized, resources, weekly_hours)
        
        # Create learning path
        path = LearningPath(
            name=f"Path to {target_role}" if target_role else "Custom Learning Path",
            description=self._generate_description(target_role, skill_gaps),
            target_role=target_role or "Custom",
            skills_to_learn=skill_gaps,
            resources=resources,
            total_duration_hours=total_hours,
            estimated_weeks=estimated_weeks,
            milestones=milestones,
        )
        
        # Calculate confidence
        confidence = self._calculate_confidence(skill_gaps, resources)
        
        return PredictionResult(
            prediction=path,
            confidence=confidence,
            explanations=self._generate_explanations(path, weekly_hours),
            factors={
                "skills_to_learn": len(skill_gaps),
                "resources_found": len(resources),
                "coverage": len(resources) / max(len(skill_gaps), 1),
            },
            metadata={
                "target_role": target_role,
                "weekly_hours": weekly_hours,
                "current_skills_count": len(current),
            },
            model_version=self.model_version,
        )
    
    def _get_role_skills(self, role: str) -> set:
        """Get required skills for a role."""
        role_key = role.lower().replace(" ", "_")
        
        if role_key in LEARNING_PATH_TEMPLATES:
            return set(LEARNING_PATH_TEMPLATES[role_key]["skills"])
        
        # Fallback: look up in career taxonomy
        from services.ml.career_predictor import CAREER_TAXONOMY
        
        for career_id, career_data in CAREER_TAXONOMY.items():
            if role_key in career_id or career_id in role_key:
                skills = career_data.get("required_skills", [])
                skills += career_data.get("preferred_skills", [])[:3]
                return set(s.lower() for s in skills)
        
        return set()
    
    def _prioritize_skills(
        self, 
        skills: List[str],
        target_role: str = None,
    ) -> List[tuple]:
        """Prioritize skills based on career impact."""
        prioritized = []
        
        for skill in skills:
            # Get skill data
            skill_data = SKILL_TAXONOMY.get(skill.lower(), {})
            demand = skill_data.get("demand_score", 0.5)
            
            # Determine priority
            if demand >= 0.9:
                priority = "high"
            elif demand >= 0.7:
                priority = "medium"
            else:
                priority = "low"
            
            # Check prerequisites (some skills should come first)
            prerequisites = {
                "react": ["javascript"],
                "node.js": ["javascript"],
                "django": ["python"],
                "deep learning": ["machine learning", "python"],
                "kubernetes": ["docker"],
                "mlops": ["machine learning", "docker"],
            }
            
            # Boost priority if it's a prerequisite for other skills
            for skill_name, prereqs in prerequisites.items():
                if skill.lower() in prereqs and skill_name in [s.lower() for s in skills]:
                    priority = "high"
                    break
            
            prioritized.append((skill, priority))
        
        # Sort by priority
        priority_order = {"high": 0, "medium": 1, "low": 2}
        prioritized.sort(key=lambda x: priority_order[x[1]])
        
        return prioritized
    
    def _get_resources_for_skill(
        self,
        skill: str,
        priority: str,
        preferred_types: List[str] = None,
    ) -> List[LearningResource]:
        """Get learning resources for a skill."""
        skill_lower = skill.lower()
        resources = []
        
        skill_resources = LEARNING_RESOURCES.get(skill_lower, [])
        
        if not skill_resources:
            # Generic fallback
            resources.append(LearningResource(
                skill=skill,
                title=f"Learn {skill.title()}",
                provider="Udemy",
                resource_type="course",
                duration_hours=20,
                level="beginner",
                rating=4.5,
                priority=priority,
            ))
            return resources
        
        # Filter by preferred types if specified
        if preferred_types:
            skill_resources = [
                r for r in skill_resources 
                if r["type"] in preferred_types
            ] or skill_resources[:1]
        
        # Get top 2 resources for each skill
        for resource_data in skill_resources[:2]:
            resource = LearningResource(
                skill=skill,
                title=resource_data["title"],
                provider=resource_data["provider"],
                resource_type=resource_data["type"],
                duration_hours=resource_data["duration_hours"],
                level=resource_data["level"],
                rating=resource_data["rating"],
                url=resource_data.get("url"),
                priority=priority,
            )
            resources.append(resource)
        
        return resources
    
    def _generate_milestones(
        self,
        prioritized_skills: List[tuple],
        resources: List[LearningResource],
        weekly_hours: int,
    ) -> List[Dict[str, Any]]:
        """Generate learning milestones."""
        milestones = []
        accumulated_hours = 0
        current_week = 0
        
        skill_groups = {}
        for skill, priority in prioritized_skills:
            skill_resources = [r for r in resources if r.skill.lower() == skill.lower()]
            skill_hours = sum(r.duration_hours for r in skill_resources)
            skill_groups[skill] = skill_hours
        
        for skill, hours in skill_groups.items():
            accumulated_hours += hours
            weeks_to_complete = max(1, accumulated_hours // weekly_hours)
            
            milestones.append({
                "skill": skill,
                "week": weeks_to_complete,
                "description": f"Complete {skill.title()} learning",
                "hours": hours,
            })
        
        return milestones
    
    def _generate_description(
        self, 
        target_role: str, 
        skill_gaps: List[str]
    ) -> str:
        """Generate learning path description."""
        if target_role:
            return f"A personalized learning path to become a {target_role}. " \
                   f"This path covers {len(skill_gaps)} skills including " \
                   f"{', '.join(skill_gaps[:3])}{'...' if len(skill_gaps) > 3 else ''}."
        else:
            return f"A custom learning path covering {len(skill_gaps)} skills."
    
    def _calculate_confidence(
        self, 
        skill_gaps: List[str], 
        resources: List[LearningResource]
    ) -> float:
        """Calculate recommendation confidence."""
        if not skill_gaps:
            return 0.5
        
        # Check how many skills have resources
        skills_with_resources = set(r.skill.lower() for r in resources)
        coverage = len(skills_with_resources) / len(skill_gaps)
        
        # Check average resource rating
        avg_rating = sum(r.rating for r in resources) / len(resources) if resources else 0
        rating_factor = avg_rating / 5.0
        
        return min(0.9, 0.5 + 0.3 * coverage + 0.2 * rating_factor)
    
    def _generate_explanations(
        self, 
        path: LearningPath,
        weekly_hours: int,
    ) -> List[str]:
        """Generate explanation text."""
        explanations = []
        
        explanations.append(
            f"This learning path includes {len(path.resources)} resources "
            f"covering {len(path.skills_to_learn)} skills."
        )
        
        explanations.append(
            f"At {weekly_hours} hours per week, you can complete this path "
            f"in approximately {path.estimated_weeks} weeks."
        )
        
        high_priority = [r for r in path.resources if r.priority == "high"]
        if high_priority:
            explanations.append(
                f"Focus first on: {', '.join(set(r.skill for r in high_priority[:3]))}"
            )
        
        return explanations
    
    def recommend_next_resource(
        self,
        completed_resources: List[str],
        learning_path: LearningPath,
    ) -> Optional[LearningResource]:
        """Recommend the next resource to study."""
        completed_lower = set(r.lower() for r in completed_resources)
        
        for resource in learning_path.resources:
            if resource.title.lower() not in completed_lower:
                return resource
        
        return None


# Singleton instance
_recommender_instance: Optional[LearningRecommender] = None


def get_learning_recommender() -> LearningRecommender:
    """Get or create singleton LearningRecommender instance."""
    global _recommender_instance
    if _recommender_instance is None:
        _recommender_instance = LearningRecommender()
    return _recommender_instance
