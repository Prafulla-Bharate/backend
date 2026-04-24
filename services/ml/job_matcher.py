"""
Job Matching ML Service
========================
TF-IDF based job matching without LLM dependency.

Real-world systems like LinkedIn, Indeed use:
1. TF-IDF vectorization for text similarity
2. Cosine similarity for matching
3. Weighted scoring (skills, experience, location)
4. Personalization based on user behavior

This module provides:
- Skill-based matching using TF-IDF
- Multi-factor scoring algorithm
- Personalized ranking based on user profile
- No LLM dependency - pure ML matching

Usage:
    matcher = JobMatcher()
    matches = matcher.match_jobs(user_profile, jobs)
"""

import re
import math
import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from collections import Counter

logger = logging.getLogger(__name__)


# =============================================================================
# SKILL SYNONYMS AND MAPPINGS
# =============================================================================

SKILL_SYNONYMS = {
    # Programming languages
    "python": ["python3", "python2", "py"],
    "javascript": ["js", "es6", "es2015", "ecmascript"],
    "typescript": ["ts"],
    "golang": ["go"],
    "csharp": ["c#", "c-sharp"],
    "cplusplus": ["c++", "cpp"],
    
    # Frameworks
    "react": ["reactjs", "react.js"],
    "angular": ["angularjs", "angular.js"],
    "vue": ["vuejs", "vue.js"],
    "node": ["nodejs", "node.js"],
    "express": ["expressjs", "express.js"],
    "django": ["django rest framework", "drf"],
    "spring": ["spring boot", "springboot"],
    "dotnet": [".net", "asp.net", ".net core"],
    
    # Databases
    "postgresql": ["postgres", "psql"],
    "mongodb": ["mongo"],
    "elasticsearch": ["elastic", "es"],
    "redis": ["redis cache"],
    
    # Cloud
    "aws": ["amazon web services", "amazon aws"],
    "gcp": ["google cloud", "google cloud platform"],
    "azure": ["microsoft azure"],
    
    # DevOps
    "kubernetes": ["k8s"],
    "docker": ["containerization"],
    "ci/cd": ["cicd", "ci cd", "continuous integration"],
    
    # Data Science
    "machine learning": ["ml", "machine-learning"],
    "deep learning": ["dl", "deep-learning"],
    "natural language processing": ["nlp"],
    "computer vision": ["cv", "image processing"],
    
    # Soft skills
    "communication": ["communication skills", "verbal communication"],
    "leadership": ["team leadership", "people management"],
    "problem solving": ["problem-solving", "analytical skills"],
}

# Create reverse mapping
SKILL_TO_CANONICAL = {}
for canonical, synonyms in SKILL_SYNONYMS.items():
    SKILL_TO_CANONICAL[canonical.lower()] = canonical
    for syn in synonyms:
        SKILL_TO_CANONICAL[syn.lower()] = canonical


# =============================================================================
# INDIA-SPECIFIC DATA
# =============================================================================

INDIA_CITIES = {
    "tier1": ["mumbai", "delhi", "bangalore", "bengaluru", "hyderabad", "chennai", "kolkata", "pune"],
    "tier2": ["ahmedabad", "jaipur", "lucknow", "kanpur", "nagpur", "indore", "thane", "bhopal", "visakhapatnam", "chandigarh", "gurgaon", "gurugram", "noida", "ghaziabad", "kochi", "coimbatore"],
    "tier3": ["vadodara", "ludhiana", "agra", "nashik", "faridabad", "meerut", "rajkot", "varanasi", "srinagar", "aurangabad", "dhanbad", "amritsar", "jodhpur", "madurai", "raipur", "kota", "guwahati"]
}

# City distance matrix (simplified - same tier = close, different tier = far)
def get_city_distance(city1: str, city2: str) -> int:
    """Get approximate distance score between cities (0-100, 0 = same city)."""
    city1, city2 = city1.lower(), city2.lower()
    
    if city1 == city2:
        return 0
    
    # Same metro area
    metro_areas = [
        ["mumbai", "thane", "navi mumbai"],
        ["delhi", "noida", "gurgaon", "gurugram", "ghaziabad", "faridabad"],
        ["bangalore", "bengaluru"],
        ["hyderabad", "secunderabad"],
        ["kolkata", "howrah"],
    ]
    
    for metro in metro_areas:
        if city1 in metro and city2 in metro:
            return 10
    
    # Find tiers
    tier1, tier2 = None, None
    for tier_name, cities in INDIA_CITIES.items():
        if city1 in cities:
            tier1 = tier_name
        if city2 in cities:
            tier2 = tier_name
    
    if tier1 == tier2:
        return 30  # Same tier, different city
    elif tier1 and tier2:
        return 50  # Different tiers
    else:
        return 70  # Unknown city


EXPERIENCE_LEVEL_MAPPING = {
    "fresher": (0, 1),
    "junior": (0, 2),
    "entry": (0, 2),
    "mid": (2, 5),
    "mid-level": (2, 5),
    "senior": (5, 10),
    "lead": (7, 15),
    "principal": (10, 20),
    "architect": (8, 20),
    "manager": (5, 15),
    "director": (10, 25),
    "vp": (15, 30),
    "executive": (15, 30),
}


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class UserProfile:
    """User profile for job matching."""
    skills: List[str] = field(default_factory=list)
    experience_years: float = 0
    current_title: str = ""
    preferred_titles: List[str] = field(default_factory=list)
    location: str = ""
    preferred_locations: List[str] = field(default_factory=list)
    remote_preference: str = "hybrid"  # onsite, remote, hybrid
    min_salary: int = 0  # in LPA
    max_salary: int = 0
    education: str = ""
    industries: List[str] = field(default_factory=list)
    company_size_preference: str = ""  # startup, mid, enterprise
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class JobPosting:
    """Job posting for matching."""
    id: str = ""
    title: str = ""
    company: str = ""
    location: str = ""
    description: str = ""
    required_skills: List[str] = field(default_factory=list)
    preferred_skills: List[str] = field(default_factory=list)
    experience_min: int = 0
    experience_max: int = 10
    salary_min: int = 0  # in LPA
    salary_max: int = 0
    job_type: str = "full-time"  # full-time, part-time, contract, internship
    remote_option: str = "onsite"  # onsite, remote, hybrid
    industry: str = ""
    company_size: str = ""
    posted_date: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MatchResult:
    """Result of job matching."""
    job: JobPosting
    overall_score: float = 0
    skill_score: float = 0
    experience_score: float = 0
    location_score: float = 0
    salary_score: float = 0
    title_score: float = 0
    matched_skills: List[str] = field(default_factory=list)
    missing_skills: List[str] = field(default_factory=list)
    match_reasons: List[str] = field(default_factory=list)
    improvement_suggestions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result["job"] = self.job.to_dict()
        return result


# =============================================================================
# TF-IDF VECTORIZER (Simplified - no sklearn dependency)
# =============================================================================

class SimpleTFIDF:
    """
    Simple TF-IDF implementation without external dependencies.
    For production, consider using sklearn's TfidfVectorizer.
    """
    
    def __init__(self):
        self.vocabulary = {}
        self.idf = {}
        self.documents = []
    
    def fit(self, documents: List[str]) -> "SimpleTFIDF":
        """Fit the TF-IDF model on documents."""
        self.documents = documents
        
        # Build vocabulary
        all_words = set()
        doc_word_counts = []
        
        for doc in documents:
            words = self._tokenize(doc)
            word_count = Counter(words)
            doc_word_counts.append(word_count)
            all_words.update(words)
        
        self.vocabulary = {word: idx for idx, word in enumerate(sorted(all_words))}
        
        # Calculate IDF
        n_docs = len(documents)
        for word in self.vocabulary:
            doc_freq = sum(1 for wc in doc_word_counts if word in wc)
            self.idf[word] = math.log(n_docs / (1 + doc_freq)) + 1
        
        return self
    
    def transform(self, documents: List[str]) -> List[Dict[str, float]]:
        """Transform documents to TF-IDF vectors."""
        vectors = []
        
        for doc in documents:
            words = self._tokenize(doc)
            word_count = Counter(words)
            total_words = len(words)
            
            vector = {}
            for word, count in word_count.items():
                if word in self.vocabulary:
                    tf = count / total_words if total_words > 0 else 0
                    tfidf = tf * self.idf.get(word, 1)
                    vector[word] = tfidf
            
            vectors.append(vector)
        
        return vectors
    
    def fit_transform(self, documents: List[str]) -> List[Dict[str, float]]:
        """Fit and transform in one step."""
        self.fit(documents)
        return self.transform(documents)
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into words."""
        text = text.lower()
        words = re.findall(r'\b\w+\b', text)
        return [w for w in words if len(w) > 1]
    
    @staticmethod
    def cosine_similarity(vec1: Dict[str, float], vec2: Dict[str, float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if not vec1 or not vec2:
            return 0
        
        # Get common words
        common_words = set(vec1.keys()) & set(vec2.keys())
        
        if not common_words:
            return 0
        
        # Calculate dot product
        dot_product = sum(vec1[w] * vec2[w] for w in common_words)
        
        # Calculate magnitudes
        mag1 = math.sqrt(sum(v ** 2 for v in vec1.values()))
        mag2 = math.sqrt(sum(v ** 2 for v in vec2.values()))
        
        if mag1 == 0 or mag2 == 0:
            return 0
        
        return dot_product / (mag1 * mag2)


# =============================================================================
# JOB MATCHER
# =============================================================================

class JobMatcher:
    """
    Match jobs to user profiles using ML techniques.
    No LLM dependency - pure algorithmic matching.
    
    Scoring weights:
    - Skills: 40%
    - Experience: 25%
    - Location: 15%
    - Salary: 10%
    - Title: 10%
    """
    
    WEIGHTS = {
        "skills": 0.40,
        "experience": 0.25,
        "location": 0.15,
        "salary": 0.10,
        "title": 0.10,
    }
    
    def __init__(self):
        self.tfidf = SimpleTFIDF()
    
    def match_jobs(
        self,
        user_profile: UserProfile,
        jobs: List[JobPosting],
        limit: int = 20
    ) -> List[MatchResult]:
        """
        Match jobs to user profile.
        
        Args:
            user_profile: User's profile
            jobs: List of job postings
            limit: Maximum number of results
        
        Returns:
            List of MatchResult sorted by score
        """
        results = []
        
        for job in jobs:
            result = self._match_single_job(user_profile, job)
            results.append(result)
        
        # Sort by overall score
        results.sort(key=lambda x: x.overall_score, reverse=True)
        
        return results[:limit]
    
    def _match_single_job(
        self,
        user_profile: UserProfile,
        job: JobPosting
    ) -> MatchResult:
        """Match a single job to user profile."""
        result = MatchResult(job=job)
        
        # 1. Skill Matching (40%)
        skill_result = self._calculate_skill_score(
            user_profile.skills,
            job.required_skills,
            job.preferred_skills
        )
        result.skill_score = skill_result["score"]
        result.matched_skills = skill_result["matched"]
        result.missing_skills = skill_result["missing"]
        
        # 2. Experience Matching (25%)
        result.experience_score = self._calculate_experience_score(
            user_profile.experience_years,
            job.experience_min,
            job.experience_max
        )
        
        # 3. Location Matching (15%)
        result.location_score = self._calculate_location_score(
            user_profile.location,
            user_profile.preferred_locations,
            job.location,
            user_profile.remote_preference,
            job.remote_option
        )
        
        # 4. Salary Matching (10%)
        result.salary_score = self._calculate_salary_score(
            user_profile.min_salary,
            user_profile.max_salary,
            job.salary_min,
            job.salary_max
        )
        
        # 5. Title Matching (10%)
        result.title_score = self._calculate_title_score(
            user_profile.current_title,
            user_profile.preferred_titles,
            job.title
        )
        
        # Calculate overall score
        result.overall_score = (
            result.skill_score * self.WEIGHTS["skills"] +
            result.experience_score * self.WEIGHTS["experience"] +
            result.location_score * self.WEIGHTS["location"] +
            result.salary_score * self.WEIGHTS["salary"] +
            result.title_score * self.WEIGHTS["title"]
        )
        
        # Generate match reasons
        result.match_reasons = self._generate_match_reasons(result)
        
        # Generate improvement suggestions
        result.improvement_suggestions = self._generate_suggestions(result)
        
        return result
    
    def _calculate_skill_score(
        self,
        user_skills: List[str],
        required_skills: List[str],
        preferred_skills: List[str]
    ) -> Dict[str, Any]:
        """Calculate skill matching score."""
        if not required_skills and not preferred_skills:
            return {"score": 50, "matched": [], "missing": []}
        
        # Normalize skills
        user_skills_normalized = self._normalize_skills(user_skills)
        required_normalized = self._normalize_skills(required_skills)
        preferred_normalized = self._normalize_skills(preferred_skills)
        
        # Match required skills
        matched_required = []
        missing_required = []
        
        for skill in required_normalized:
            if skill in user_skills_normalized or self._fuzzy_skill_match(skill, user_skills_normalized):
                matched_required.append(skill)
            else:
                missing_required.append(skill)
        
        # Match preferred skills
        matched_preferred = []
        for skill in preferred_normalized:
            if skill in user_skills_normalized or self._fuzzy_skill_match(skill, user_skills_normalized):
                matched_preferred.append(skill)
        
        # Calculate score
        required_score = 0
        if required_normalized:
            required_score = (len(matched_required) / len(required_normalized)) * 80
        else:
            required_score = 50
        
        preferred_score = 0
        if preferred_normalized:
            preferred_score = (len(matched_preferred) / len(preferred_normalized)) * 20
        
        total_score = min(100, required_score + preferred_score)
        
        return {
            "score": total_score,
            "matched": matched_required + matched_preferred,
            "missing": missing_required,
        }
    
    def _normalize_skills(self, skills: List[str]) -> set:
        """Normalize skills to canonical form."""
        normalized = set()
        for skill in skills:
            skill_lower = skill.lower().strip()
            canonical = SKILL_TO_CANONICAL.get(skill_lower, skill_lower)
            normalized.add(canonical)
        return normalized
    
    def _fuzzy_skill_match(self, skill: str, skill_set: set) -> bool:
        """Check for fuzzy skill matching."""
        skill = skill.lower()
        
        for s in skill_set:
            # Substring match
            if skill in s or s in skill:
                return True
            
            # Partial word match
            skill_words = set(skill.split())
            s_words = set(s.split())
            if skill_words & s_words:
                return True
        
        return False
    
    def _calculate_experience_score(
        self,
        user_exp: float,
        min_exp: int,
        max_exp: int
    ) -> float:
        """Calculate experience matching score."""
        if min_exp == 0 and max_exp == 0:
            return 70  # No experience requirement
        
        if max_exp == 0:
            max_exp = min_exp + 5
        
        if min_exp <= user_exp <= max_exp:
            # Perfect match
            return 100
        elif user_exp < min_exp:
            # Under-qualified
            gap = min_exp - user_exp
            if gap <= 1:
                return 70
            elif gap <= 2:
                return 50
            else:
                return max(0, 30 - gap * 5)
        else:
            # Over-qualified
            excess = user_exp - max_exp
            if excess <= 2:
                return 80
            elif excess <= 5:
                return 60
            else:
                return 40  # Might be overqualified
    
    def _calculate_location_score(
        self,
        user_location: str,
        preferred_locations: List[str],
        job_location: str,
        remote_pref: str,
        job_remote: str
    ) -> float:
        """Calculate location matching score."""
        # Remote work matching
        if job_remote == "remote" or remote_pref == "remote":
            if job_remote == "remote":
                return 100 if remote_pref in ["remote", "hybrid"] else 70
        
        if job_remote == "hybrid" and remote_pref in ["remote", "hybrid"]:
            return 90
        
        # Location matching
        if not job_location:
            return 70
        
        job_loc = job_location.lower()
        user_loc = user_location.lower()
        pref_locs = [loc.lower() for loc in preferred_locations]
        
        # Exact match
        if job_loc == user_loc:
            return 100
        
        # Preferred location match
        if job_loc in pref_locs:
            return 95
        
        # Calculate distance score
        distance = get_city_distance(user_loc, job_loc)
        
        if distance <= 10:
            return 95  # Same metro area
        elif distance <= 30:
            return 80  # Same tier
        elif distance <= 50:
            return 60  # Different tier
        else:
            return 40  # Far away
    
    def _calculate_salary_score(
        self,
        user_min: int,
        user_max: int,
        job_min: int,
        job_max: int
    ) -> float:
        """Calculate salary matching score."""
        if job_min == 0 and job_max == 0:
            return 70  # No salary info
        
        if user_min == 0 and user_max == 0:
            return 70  # User has no preference
        
        # Calculate overlap
        if job_max == 0:
            job_max = job_min * 1.5
        
        if user_max == 0:
            user_max = user_min * 1.5
        
        # Check for overlap
        if job_max < user_min:
            # Job pays less than user wants
            gap_percent = (user_min - job_max) / user_min * 100
            if gap_percent <= 10:
                return 60
            elif gap_percent <= 20:
                return 40
            else:
                return 20
        elif job_min > user_max:
            # Job pays more (unlikely to be a problem)
            return 100
        else:
            # Overlapping ranges
            overlap_start = max(user_min, job_min)
            overlap_end = min(user_max, job_max)
            
            user_range = user_max - user_min
            if user_range > 0:
                overlap_percent = (overlap_end - overlap_start) / user_range * 100
                return min(100, 70 + overlap_percent * 0.3)
            else:
                return 85
    
    def _calculate_title_score(
        self,
        current_title: str,
        preferred_titles: List[str],
        job_title: str
    ) -> float:
        """Calculate job title matching score."""
        if not job_title:
            return 50
        
        job_title_lower = job_title.lower()
        current_lower = current_title.lower() if current_title else ""
        pref_lower = [t.lower() for t in preferred_titles]
        
        # Exact match with preferred
        for pref in pref_lower:
            if pref in job_title_lower or job_title_lower in pref:
                return 100
        
        # Match with current title
        if current_lower:
            # Same level progression
            level_keywords = ["junior", "senior", "lead", "principal", "staff", "manager", "director"]
            
            for kw in level_keywords:
                if kw in current_lower and kw in job_title_lower:
                    return 90
            
            # Role match
            role_keywords = ["engineer", "developer", "analyst", "designer", "architect", "scientist"]
            for kw in role_keywords:
                if kw in current_lower and kw in job_title_lower:
                    return 85
            
            # Some overlap
            current_words = set(current_lower.split())
            job_words = set(job_title_lower.split())
            if current_words & job_words:
                return 75
        
        return 50  # No clear match
    
    def _generate_match_reasons(self, result: MatchResult) -> List[str]:
        """Generate human-readable match reasons."""
        reasons = []
        
        if result.skill_score >= 80:
            reasons.append(f"Strong skill match ({len(result.matched_skills)} skills matched)")
        elif result.skill_score >= 60:
            reasons.append(f"Good skill match ({len(result.matched_skills)} skills matched)")
        
        if result.experience_score >= 90:
            reasons.append("Experience level is a perfect fit")
        elif result.experience_score >= 70:
            reasons.append("Experience level is a good fit")
        
        if result.location_score >= 90:
            reasons.append("Location preference matched")
        
        if result.salary_score >= 80:
            reasons.append("Salary range aligns with expectations")
        
        if result.title_score >= 80:
            reasons.append("Job title matches career goals")
        
        return reasons[:4]
    
    def _generate_suggestions(self, result: MatchResult) -> List[str]:
        """Generate improvement suggestions."""
        suggestions = []
        
        if result.missing_skills:
            skills_str = ", ".join(result.missing_skills[:3])
            suggestions.append(f"Consider learning: {skills_str}")
        
        if result.experience_score < 60:
            suggestions.append("Gain more experience in the required areas")
        
        if result.skill_score < 60 and not result.missing_skills:
            suggestions.append("Highlight relevant project experience")
        
        return suggestions[:3]
    
    def quick_score(
        self,
        user_skills: List[str],
        job_skills: List[str]
    ) -> float:
        """Quick skill-only matching score."""
        if not job_skills:
            return 50
        
        user_normalized = self._normalize_skills(user_skills)
        job_normalized = self._normalize_skills(job_skills)
        
        matched = sum(
            1 for skill in job_normalized 
            if skill in user_normalized or self._fuzzy_skill_match(skill, user_normalized)
        )
        
        return (matched / len(job_normalized)) * 100 if job_normalized else 50


# =============================================================================
# JOB RANKER - Personalized ranking
# =============================================================================

class JobRanker:
    """
    Personalized job ranking based on user behavior.
    Learns from user interactions (views, applications, saves).
    """
    
    def __init__(self):
        self.matcher = JobMatcher()
        self.user_preferences = {}  # user_id -> preferences learned from behavior
    
    def rank_jobs(
        self,
        user_profile: UserProfile,
        jobs: List[JobPosting],
        user_history: Dict[str, Any] = None,
        limit: int = 20
    ) -> List[MatchResult]:
        """
        Rank jobs with personalization based on user history.
        
        Args:
            user_profile: User's profile
            jobs: List of job postings
            user_history: Dict with 'viewed', 'applied', 'saved' job IDs
            limit: Maximum results
        """
        # Get base matches
        matches = self.matcher.match_jobs(user_profile, jobs, limit=len(jobs))
        
        if not user_history:
            return matches[:limit]
        
        # Apply personalization boosts
        viewed_ids = set(user_history.get("viewed", []))
        applied_ids = set(user_history.get("applied", []))
        saved_ids = set(user_history.get("saved", []))
        
        for match in matches:
            job_id = match.job.id
            
            # Slight penalty for already viewed (user saw and didn't apply)
            if job_id in viewed_ids and job_id not in applied_ids:
                match.overall_score *= 0.95
            
            # Boost similar to applied jobs
            if applied_ids:
                applied_similarity = self._calculate_similarity_to_set(
                    match.job, 
                    [j for j in jobs if j.id in applied_ids]
                )
                match.overall_score *= (1 + applied_similarity * 0.1)
            
            # Boost similar to saved jobs
            if saved_ids:
                saved_similarity = self._calculate_similarity_to_set(
                    match.job,
                    [j for j in jobs if j.id in saved_ids]
                )
                match.overall_score *= (1 + saved_similarity * 0.05)
        
        # Re-sort
        matches.sort(key=lambda x: x.overall_score, reverse=True)
        
        return matches[:limit]
    
    def _calculate_similarity_to_set(
        self,
        job: JobPosting,
        reference_jobs: List[JobPosting]
    ) -> float:
        """Calculate average similarity to a set of jobs."""
        if not reference_jobs:
            return 0
        
        job_skills = set(s.lower() for s in job.required_skills + job.preferred_skills)
        
        similarities = []
        for ref_job in reference_jobs:
            ref_skills = set(s.lower() for s in ref_job.required_skills + ref_job.preferred_skills)
            
            if job_skills or ref_skills:
                intersection = len(job_skills & ref_skills)
                union = len(job_skills | ref_skills)
                jaccard = intersection / union if union > 0 else 0
                similarities.append(jaccard)
        
        return sum(similarities) / len(similarities) if similarities else 0


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

def get_job_matcher() -> JobMatcher:
    """Get job matcher instance."""
    return JobMatcher()


def get_job_ranker() -> JobRanker:
    """Get job ranker instance."""
    return JobRanker()
