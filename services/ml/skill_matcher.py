"""
Skill Matcher Service
=====================
Advanced skill matching using semantic similarity and skill taxonomies.

This service provides:
1. Skill-to-skill similarity matching
2. Skill gap analysis
3. Skill recommendations
4. Skill clustering by category
"""

import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple
from functools import lru_cache

from services.ml.base import BaseMatcher, PredictionResult

logger = logging.getLogger(__name__)


# Comprehensive skill taxonomy with relationships
SKILL_TAXONOMY = {
    # Programming Languages
    "python": {
        "category": "programming_language",
        "level": "intermediate",
        "related": ["django", "flask", "fastapi", "pandas", "numpy", "machine learning"],
        "demand_score": 0.95,
    },
    "javascript": {
        "category": "programming_language",
        "level": "intermediate",
        "related": ["react", "node.js", "vue", "angular", "typescript"],
        "demand_score": 0.92,
    },
    "java": {
        "category": "programming_language",
        "level": "intermediate",
        "related": ["spring", "hibernate", "microservices", "android"],
        "demand_score": 0.85,
    },
    "typescript": {
        "category": "programming_language",
        "level": "intermediate",
        "related": ["javascript", "react", "angular", "node.js"],
        "demand_score": 0.88,
    },
    "go": {
        "category": "programming_language",
        "level": "intermediate",
        "related": ["kubernetes", "docker", "microservices", "cloud"],
        "demand_score": 0.80,
    },
    "rust": {
        "category": "programming_language",
        "level": "advanced",
        "related": ["systems programming", "performance", "webassembly"],
        "demand_score": 0.75,
    },
    "c++": {
        "category": "programming_language",
        "level": "advanced",
        "related": ["systems programming", "game development", "embedded"],
        "demand_score": 0.70,
    },
    "sql": {
        "category": "database",
        "level": "intermediate",
        "related": ["postgresql", "mysql", "data analysis", "etl"],
        "demand_score": 0.90,
    },
    
    # Frameworks
    "react": {
        "category": "frontend_framework",
        "level": "intermediate",
        "related": ["javascript", "typescript", "redux", "next.js"],
        "demand_score": 0.93,
    },
    "node.js": {
        "category": "backend_framework",
        "level": "intermediate",
        "related": ["javascript", "express", "rest api", "mongodb"],
        "demand_score": 0.88,
    },
    "django": {
        "category": "backend_framework",
        "level": "intermediate",
        "related": ["python", "rest api", "postgresql", "celery"],
        "demand_score": 0.82,
    },
    "spring": {
        "category": "backend_framework",
        "level": "intermediate",
        "related": ["java", "microservices", "rest api", "hibernate"],
        "demand_score": 0.78,
    },
    
    # Cloud & DevOps
    "aws": {
        "category": "cloud",
        "level": "intermediate",
        "related": ["cloud architecture", "lambda", "ec2", "s3", "devops"],
        "demand_score": 0.95,
    },
    "azure": {
        "category": "cloud",
        "level": "intermediate",
        "related": ["cloud architecture", "devops", "microsoft"],
        "demand_score": 0.85,
    },
    "docker": {
        "category": "devops",
        "level": "intermediate",
        "related": ["kubernetes", "containerization", "ci/cd", "microservices"],
        "demand_score": 0.92,
    },
    "kubernetes": {
        "category": "devops",
        "level": "advanced",
        "related": ["docker", "cloud", "microservices", "devops"],
        "demand_score": 0.90,
    },
    "terraform": {
        "category": "devops",
        "level": "intermediate",
        "related": ["infrastructure as code", "aws", "azure", "cloud"],
        "demand_score": 0.85,
    },
    "ci/cd": {
        "category": "devops",
        "level": "intermediate",
        "related": ["jenkins", "github actions", "gitlab", "automation"],
        "demand_score": 0.88,
    },
    
    # Data & ML
    "machine learning": {
        "category": "data_science",
        "level": "advanced",
        "related": ["python", "tensorflow", "pytorch", "deep learning", "statistics"],
        "demand_score": 0.92,
    },
    "deep learning": {
        "category": "data_science",
        "level": "advanced",
        "related": ["machine learning", "neural networks", "tensorflow", "pytorch"],
        "demand_score": 0.88,
    },
    "tensorflow": {
        "category": "ml_framework",
        "level": "advanced",
        "related": ["machine learning", "deep learning", "python", "keras"],
        "demand_score": 0.85,
    },
    "pytorch": {
        "category": "ml_framework",
        "level": "advanced",
        "related": ["machine learning", "deep learning", "python"],
        "demand_score": 0.87,
    },
    "data analysis": {
        "category": "data_science",
        "level": "intermediate",
        "related": ["python", "sql", "pandas", "visualization", "statistics"],
        "demand_score": 0.90,
    },
    "spark": {
        "category": "big_data",
        "level": "advanced",
        "related": ["big data", "hadoop", "scala", "data engineering"],
        "demand_score": 0.82,
    },
    
    # Soft Skills
    "leadership": {
        "category": "soft_skill",
        "level": "advanced",
        "related": ["management", "communication", "team building", "mentoring"],
        "demand_score": 0.85,
    },
    "communication": {
        "category": "soft_skill",
        "level": "intermediate",
        "related": ["presentation", "writing", "stakeholder management"],
        "demand_score": 0.90,
    },
    "problem solving": {
        "category": "soft_skill",
        "level": "intermediate",
        "related": ["analytical thinking", "critical thinking", "debugging"],
        "demand_score": 0.92,
    },
    "agile": {
        "category": "methodology",
        "level": "intermediate",
        "related": ["scrum", "kanban", "project management", "jira"],
        "demand_score": 0.85,
    },
}

# Skill category weights for matching
CATEGORY_WEIGHTS = {
    "programming_language": 1.0,
    "frontend_framework": 0.9,
    "backend_framework": 0.9,
    "cloud": 0.95,
    "devops": 0.9,
    "data_science": 0.95,
    "ml_framework": 0.85,
    "big_data": 0.85,
    "database": 0.85,
    "soft_skill": 0.7,
    "methodology": 0.6,
}


@dataclass
class SkillMatch:
    """Represents a skill match result."""
    skill: str
    similarity_score: float
    category: str
    demand_score: float
    related_skills: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill": self.skill,
            "similarity_score": round(self.similarity_score, 3),
            "category": self.category,
            "demand_score": round(self.demand_score, 3),
            "related_skills": self.related_skills[:5],
        }


@dataclass
class SkillGap:
    """Represents a skill gap with learning priority."""
    skill: str
    importance: str  # high, medium, low
    category: str
    demand_score: float
    learning_resources: List[str]
    estimated_time_weeks: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill": self.skill,
            "importance": self.importance,
            "category": self.category,
            "demand_score": round(self.demand_score, 3),
            "learning_resources": self.learning_resources,
            "estimated_time_weeks": self.estimated_time_weeks,
        }


class SkillMatcher(BaseMatcher):
    """
    Advanced skill matching using taxonomy and semantic relationships.
    
    Features:
    - Skill normalization and synonym handling
    - Category-based matching
    - Related skill discovery
    - Skill gap analysis with learning recommendations
    """
    
    def __init__(self):
        self.taxonomy = SKILL_TAXONOMY
        self.category_weights = CATEGORY_WEIGHTS
        self._build_inverted_index()
    
    def _build_inverted_index(self):
        """Build inverted index for fast skill lookup."""
        self.skill_to_category = {}
        self.category_to_skills = {}
        
        for skill, data in self.taxonomy.items():
            category = data["category"]
            self.skill_to_category[skill] = category
            
            if category not in self.category_to_skills:
                self.category_to_skills[category] = []
            self.category_to_skills[category].append(skill)
    
    def normalize_skill(self, skill: str) -> str:
        """Normalize skill name for matching."""
        # Lowercase and strip
        normalized = skill.lower().strip()
        
        # Common replacements
        replacements = {
            "js": "javascript",
            "py": "python",
            "ml": "machine learning",
            "k8s": "kubernetes",
            "react.js": "react",
            "reactjs": "react",
            "nodejs": "node.js",
            "node": "node.js",
            "postgres": "postgresql",
            "tf": "tensorflow",
        }
        
        return replacements.get(normalized, normalized)
    
    def compute_similarity(self, skill1: str, skill2: str) -> float:
        """
        Compute similarity between two skills.
        
        Uses:
        1. Exact match (1.0)
        2. Category match (0.6-0.8)
        3. Related skill connection (0.4-0.6)
        4. String similarity (0.1-0.3)
        """
        s1 = self.normalize_skill(skill1)
        s2 = self.normalize_skill(skill2)
        
        # Exact match
        if s1 == s2:
            return 1.0
        
        # Check if in same category
        cat1 = self.skill_to_category.get(s1, "unknown")
        cat2 = self.skill_to_category.get(s2, "unknown")
        
        if cat1 == cat2 and cat1 != "unknown":
            return 0.7
        
        # Check if related
        data1 = self.taxonomy.get(s1, {})
        data2 = self.taxonomy.get(s2, {})
        
        related1 = set(data1.get("related", []))
        related2 = set(data2.get("related", []))
        
        if s2 in related1 or s1 in related2:
            return 0.5
        
        # Check overlap in related skills
        overlap = related1 & related2
        if overlap:
            return 0.3 + 0.1 * min(len(overlap), 3)
        
        # String similarity (Jaccard on characters)
        chars1 = set(s1)
        chars2 = set(s2)
        if chars1 and chars2:
            jaccard = len(chars1 & chars2) / len(chars1 | chars2)
            return 0.1 * jaccard
        
        return 0.0
    
    def find_matches(
        self, 
        skill: str, 
        candidates: List[str] = None, 
        top_k: int = 10
    ) -> List[SkillMatch]:
        """Find top matching skills from candidates or taxonomy."""
        normalized = self.normalize_skill(skill)
        
        if candidates is None:
            candidates = list(self.taxonomy.keys())
        
        matches = []
        for candidate in candidates:
            norm_candidate = self.normalize_skill(candidate)
            similarity = self.compute_similarity(normalized, norm_candidate)
            
            data = self.taxonomy.get(norm_candidate, {
                "category": "unknown",
                "demand_score": 0.5,
                "related": [],
            })
            
            match = SkillMatch(
                skill=candidate,
                similarity_score=similarity,
                category=data.get("category", "unknown"),
                demand_score=data.get("demand_score", 0.5),
                related_skills=data.get("related", []),
            )
            matches.append(match)
        
        # Sort by similarity
        matches.sort(key=lambda x: x.similarity_score, reverse=True)
        return matches[:top_k]
    
    def analyze_skill_gaps(
        self,
        user_skills: List[str],
        target_skills: List[str],
        required_skills: List[str] = None,
    ) -> List[SkillGap]:
        """
        Analyze skill gaps and provide learning recommendations.
        
        Args:
            user_skills: Skills the user currently has
            target_skills: Skills needed for target role
            required_skills: Subset of target_skills that are mandatory
        """
        user_normalized = {self.normalize_skill(s) for s in user_skills}
        target_normalized = {self.normalize_skill(s) for s in target_skills}
        required_normalized = {self.normalize_skill(s) for s in (required_skills or [])}
        
        # Find missing skills
        missing = target_normalized - user_normalized
        
        gaps = []
        for skill in missing:
            data = self.taxonomy.get(skill, {})
            
            # Determine importance
            if skill in required_normalized:
                importance = "high"
            elif data.get("demand_score", 0) > 0.85:
                importance = "high"
            elif data.get("demand_score", 0) > 0.7:
                importance = "medium"
            else:
                importance = "low"
            
            # Estimate learning time based on level
            level = data.get("level", "intermediate")
            time_map = {"beginner": 2, "intermediate": 4, "advanced": 8}
            estimated_time = time_map.get(level, 4)
            
            # Check if user has related skills (faster learning)
            related = set(data.get("related", []))
            if related & user_normalized:
                estimated_time = max(1, estimated_time - 1)
            
            gap = SkillGap(
                skill=skill,
                importance=importance,
                category=data.get("category", "unknown"),
                demand_score=data.get("demand_score", 0.5),
                learning_resources=self._get_learning_resources(skill),
                estimated_time_weeks=estimated_time,
            )
            gaps.append(gap)
        
        # Sort by importance then demand score
        importance_order = {"high": 0, "medium": 1, "low": 2}
        gaps.sort(key=lambda x: (importance_order[x.importance], -x.demand_score))
        
        return gaps
    
    def _get_learning_resources(self, skill: str) -> List[str]:
        """Get learning resource suggestions for a skill."""
        # This would ideally connect to a learning content database
        resources = {
            "python": ["Python Documentation", "Coursera Python for Everybody", "Real Python"],
            "javascript": ["MDN Web Docs", "JavaScript.info", "freeCodeCamp"],
            "react": ["React Official Docs", "Udemy React Course", "React Tutorial"],
            "aws": ["AWS Training", "A Cloud Guru", "AWS Certified Solutions Architect"],
            "machine learning": ["Coursera ML by Andrew Ng", "Fast.ai", "Kaggle Learn"],
            "docker": ["Docker Documentation", "Docker Getting Started", "Play with Docker"],
            "kubernetes": ["Kubernetes.io", "Kubernetes the Hard Way", "CKAD Training"],
            "sql": ["SQLZoo", "Mode SQL Tutorial", "PostgreSQL Tutorial"],
        }
        
        return resources.get(skill, ["Udemy", "Coursera", "YouTube tutorials"])
    
    def recommend_next_skills(
        self,
        current_skills: List[str],
        career_target: str = None,
        top_k: int = 5,
    ) -> List[SkillMatch]:
        """
        Recommend next skills to learn based on current skills and career target.
        
        Uses:
        1. Related skills from current skillset
        2. High-demand skills in target career
        3. Skills that unlock more opportunities
        """
        current_normalized = {self.normalize_skill(s) for s in current_skills}
        
        # Collect related skills from current skills
        related_candidates = set()
        for skill in current_normalized:
            data = self.taxonomy.get(skill, {})
            related_candidates.update(data.get("related", []))
        
        # Remove skills user already has
        related_candidates -= current_normalized
        
        # Score candidates
        recommendations = []
        for skill in related_candidates:
            data = self.taxonomy.get(skill, {})
            
            # Base score from demand
            score = data.get("demand_score", 0.5)
            
            # Boost if multiple current skills relate to it
            connection_count = sum(
                1 for curr in current_normalized
                if skill in self.taxonomy.get(curr, {}).get("related", [])
            )
            score += 0.1 * min(connection_count, 3)
            
            # Boost for category weight
            category = data.get("category", "unknown")
            score *= self.category_weights.get(category, 0.5)
            
            match = SkillMatch(
                skill=skill,
                similarity_score=min(score, 1.0),
                category=category,
                demand_score=data.get("demand_score", 0.5),
                related_skills=data.get("related", []),
            )
            recommendations.append(match)
        
        recommendations.sort(key=lambda x: x.similarity_score, reverse=True)
        return recommendations[:top_k]
    
    def get_skill_info(self, skill: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a skill."""
        normalized = self.normalize_skill(skill)
        data = self.taxonomy.get(normalized)
        
        if not data:
            return None
        
        return {
            "skill": normalized,
            "category": data["category"],
            "level": data["level"],
            "demand_score": data["demand_score"],
            "related_skills": data["related"],
            "category_weight": self.category_weights.get(data["category"], 0.5),
        }
    
    def cluster_skills(self, skills: List[str]) -> Dict[str, List[str]]:
        """Cluster skills by category."""
        clusters = {}
        
        for skill in skills:
            normalized = self.normalize_skill(skill)
            category = self.skill_to_category.get(normalized, "other")
            
            if category not in clusters:
                clusters[category] = []
            clusters[category].append(skill)
        
        return clusters
    
    def get_skill_gaps(
        self,
        current_skills: List[str],
        target_role: str,
    ) -> Dict[str, Any]:
        """
        Get skill gaps for a target role.
        
        This is a convenience wrapper around analyze_skill_gaps that 
        looks up the required skills for a role from CAREER_TAXONOMY.
        
        Args:
            current_skills: Skills the user currently has
            target_role: Target role/career title
            
        Returns:
            Dictionary with skill gap analysis results
        """
        # Import career taxonomy to get role skills
        try:
            from services.ml.career_predictor import CAREER_TAXONOMY
        except ImportError:
            CAREER_TAXONOMY = {}
        
        # Normalize role name for lookup
        role_key = target_role.lower().replace(" ", "_").replace("-", "_")
        
        # Try to find the role in taxonomy
        role_data = CAREER_TAXONOMY.get(role_key, {})
        
        # If not found, try partial match
        if not role_data:
            for key, data in CAREER_TAXONOMY.items():
                if role_key in key or key in role_key:
                    role_data = data
                    break
                # Also check title
                if data.get("title", "").lower().replace(" ", "_") == role_key:
                    role_data = data
                    break
        
        # Get target skills from role
        required_skills = role_data.get("required_skills", [])
        preferred_skills = role_data.get("preferred_skills", [])
        target_skills = list(set(required_skills + preferred_skills))
        
        # If no role data found, return empty result
        if not target_skills:
            logger.warning(f"No skill data found for role: {target_role}")
            return {
                "gaps": [],
                "match_percentage": 0,
                "priority_skills": [],
                "role": target_role,
            }
        
        # Use analyze_skill_gaps for the actual analysis
        gaps = self.analyze_skill_gaps(
            user_skills=current_skills,
            target_skills=target_skills,
            required_skills=required_skills
        )
        
        # Calculate match percentage
        current_normalized = {self.normalize_skill(s) for s in current_skills}
        target_normalized = {self.normalize_skill(s) for s in target_skills}
        matched = current_normalized & target_normalized
        match_percentage = len(matched) / len(target_normalized) * 100 if target_normalized else 0
        
        # Convert gaps to dictionaries
        gap_dicts = [gap.to_dict() for gap in gaps]
        
        # Get priority skills (high importance gaps)
        priority_skills = [g["skill"] for g in gap_dicts if g.get("importance") == "high"][:5]
        
        return {
            "gaps": gap_dicts,
            "match_percentage": round(match_percentage, 1),
            "priority_skills": priority_skills,
            "role": target_role,
            "required_skills": required_skills,
            "total_target_skills": len(target_skills),
            "skills_matched": len(matched),
            "skills_missing": len(gaps),
        }


# Singleton instance
_matcher_instance: Optional[SkillMatcher] = None


def get_skill_matcher() -> SkillMatcher:
    """Get or create singleton SkillMatcher instance."""
    global _matcher_instance
    if _matcher_instance is None:
        _matcher_instance = SkillMatcher()
    return _matcher_instance
