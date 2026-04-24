"""
Profile Services
================
Business logic for profile-related operations.
"""

from typing import Any, Dict

from django.db.models import QuerySet

from apps.profile.models import (
    UserEducation,
    UserExperience,
)


class ProfileService:
    """Service for user profile operations."""
    
    @staticmethod
    def calculate_completeness(user) -> int:
        """
        Calculate profile completeness score (0-100).
        
        Scoring weights:
        - Basic info (name, email, phone): 15%
        - Education: 15%
        - Experience: 20%
        - Skills: 20%
        - Interests: 5%
        - Certifications: 10%
        - Projects: 10%
        - Languages: 5%
        """
        score = 0
        
        # Basic info (15%)
        basic_score = 0
        if user.first_name:
            basic_score += 5
        if user.last_name:
            basic_score += 5
        if user.phone:
            basic_score += 5
        score += basic_score
        
        # Education (15%)
        if user.educations.exists():
            score += 15
        
        # Experience (20%)
        experience_count = user.experiences.count()
        if experience_count >= 3:
            score += 20
        elif experience_count >= 1:
            score += 10
        
        # Skills (20%)
        skill_count = user.skills.count()
        if skill_count >= 10:
            score += 20
        elif skill_count >= 5:
            score += 15
        elif skill_count >= 1:
            score += 10
        
        # Interests (5%)
        if user.interests.exists():
            score += 5
        
        # Certifications (10%)
        if user.certifications.exists():
            score += 10
        
        # Projects (10%)
        if user.projects.exists():
            score += 10
        
        # Languages (5%)
        if user.languages.exists():
            score += 5
        
        return min(score, 100)
    
    @staticmethod
    def get_completeness_details(user) -> Dict[str, Any]:
        """Get detailed completeness breakdown."""
        sections = {
            "basic_info": {
                "score": 0,
                "max_score": 15,
                "items": []
            },
            "education": {
                "score": 0,
                "max_score": 15,
                "items": []
            },
            "experience": {
                "score": 0,
                "max_score": 20,
                "items": []
            },
            "skills": {
                "score": 0,
                "max_score": 20,
                "items": []
            },
            "interests": {
                "score": 0,
                "max_score": 5,
                "items": []
            },
            "certifications": {
                "score": 0,
                "max_score": 10,
                "items": []
            },
            "projects": {
                "score": 0,
                "max_score": 10,
                "items": []
            },
            "languages": {
                "score": 0,
                "max_score": 5,
                "items": []
            },
        }
        
        missing_sections = []
        suggestions = []
        
        # Basic info
        if user.first_name:
            sections["basic_info"]["score"] += 5
            sections["basic_info"]["items"].append("First name")
        else:
            suggestions.append("Add your first name")
        
        if user.last_name:
            sections["basic_info"]["score"] += 5
            sections["basic_info"]["items"].append("Last name")
        else:
            suggestions.append("Add your last name")
        
        if user.phone:
            sections["basic_info"]["score"] += 5
            sections["basic_info"]["items"].append("Phone number")
        else:
            suggestions.append("Add your phone number")
        
        if sections["basic_info"]["score"] == 0:
            missing_sections.append("basic_info")
        
        # Education
        education_count = user.educations.count()
        if education_count > 0:
            sections["education"]["score"] = 15
            sections["education"]["items"].append(f"{education_count} education record(s)")
        else:
            missing_sections.append("education")
            suggestions.append("Add your educational background")
        
        # Experience
        experience_count = user.experiences.count()
        if experience_count >= 3:
            sections["experience"]["score"] = 20
        elif experience_count >= 1:
            sections["experience"]["score"] = 10
            suggestions.append("Add more work experience for a complete profile")
        else:
            missing_sections.append("experience")
            suggestions.append("Add your work experience")
        sections["experience"]["items"].append(f"{experience_count} experience record(s)")
        
        # Skills
        skill_count = user.skills.count()
        if skill_count >= 10:
            sections["skills"]["score"] = 20
        elif skill_count >= 5:
            sections["skills"]["score"] = 15
            suggestions.append("Add more skills to reach 10 for a complete profile")
        elif skill_count >= 1:
            sections["skills"]["score"] = 10
            suggestions.append("Add more skills to improve your profile")
        else:
            missing_sections.append("skills")
            suggestions.append("Add your skills")
        sections["skills"]["items"].append(f"{skill_count} skill(s)")
        
        # Interests
        interest_count = user.interests.count()
        if interest_count > 0:
            sections["interests"]["score"] = 5
            sections["interests"]["items"].append(f"{interest_count} interest(s)")
        else:
            missing_sections.append("interests")
            suggestions.append("Add your interests")
        
        # Certifications
        cert_count = user.certifications.count()
        if cert_count > 0:
            sections["certifications"]["score"] = 10
            sections["certifications"]["items"].append(f"{cert_count} certification(s)")
        else:
            missing_sections.append("certifications")
            suggestions.append("Add any certifications you have")
        
        # Projects
        project_count = user.projects.count()
        if project_count > 0:
            sections["projects"]["score"] = 10
            sections["projects"]["items"].append(f"{project_count} project(s)")
        else:
            missing_sections.append("projects")
            suggestions.append("Add portfolio projects to showcase your work")
        
        # Languages
        language_count = user.languages.count()
        if language_count > 0:
            sections["languages"]["score"] = 5
            sections["languages"]["items"].append(f"{language_count} language(s)")
        else:
            missing_sections.append("languages")
            suggestions.append("Add languages you speak")
        
        overall_score = sum(s["score"] for s in sections.values())
        
        return {
            "overall_score": overall_score,
            "sections": sections,
            "missing_sections": missing_sections,
            "suggestions": suggestions[:5],  # Limit to top 5 suggestions
        }


class EducationService:
    """Service for education-related operations."""
    
    @staticmethod
    def get_user_educations(user) -> QuerySet:
        """Get all educations for a user."""
        return UserEducation.objects.filter(user=user).order_by("-end_date", "-start_date")


class ExperienceService:
    """Service for experience-related operations."""
    
    @staticmethod
    def get_user_experiences(user) -> QuerySet:
        """Get all experiences for a user."""
        return UserExperience.objects.filter(user=user).order_by("-end_date", "-start_date")
