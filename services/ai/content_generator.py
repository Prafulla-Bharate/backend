"""
Content Generator Service
=========================
AI-powered content generation for career development.

Features:
1. Cover letter generation
2. Resume bullet point optimization
3. LinkedIn summary writing
4. Career summary generation
5. Skill descriptions
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from services.ai.base import get_ai_service

logger = logging.getLogger(__name__)


@dataclass
class GeneratedContent:
    """Container for generated content."""
    content: str
    content_type: str
    word_count: int
    suggestions: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "content_type": self.content_type,
            "word_count": self.word_count,
            "suggestions": self.suggestions,
        }


class ContentGenerator:
    """
    AI-powered content generator for career materials.
    
    Generates professional content for:
    - Cover letters
    - Resume bullet points
    - LinkedIn profiles
    - Career summaries
    """
    
    def __init__(self):
        self.ai_service = get_ai_service()
    
    def generate_cover_letter(
        self,
        job_title: str,
        company: str,
        user_name: str = "[Your Name]",
        skills: List[str] = None,
        experience_highlights: List[str] = None,
        company_values: str = None,
    ) -> GeneratedContent:
        """
        Generate a customized cover letter.
        
        Args:
            job_title: Target job title
            company: Company name
            user_name: Applicant's name
            skills: Key skills to highlight
            experience_highlights: Notable achievements
            company_values: Company mission/values to reference
        """
        logger.info(f"Generating cover letter for {job_title} at {company}")
        
        skills_text = ", ".join(skills[:5]) if skills else "relevant technical skills"
        highlights = "\n".join(f"• {h}" for h in (experience_highlights or []))
        
        cover_letter = f"""Dear Hiring Manager,

I am writing to express my strong interest in the {job_title} position at {company}. With my background in {skills_text} and passion for delivering impactful solutions, I am confident I would be a valuable addition to your team.

In my recent experience, I have:
{highlights or "• Led projects that improved system performance and user satisfaction"}
• Collaborated with cross-functional teams to deliver solutions on time and within scope
• Continuously improved my skills to stay current with industry best practices

{f"I am particularly drawn to {company}'s commitment to {company_values}. " if company_values else ""}I am excited about the opportunity to contribute my expertise to help {company} achieve its goals.

I would welcome the chance to discuss how my skills and experience align with your needs. Thank you for considering my application.

Best regards,
{user_name}"""

        return GeneratedContent(
            content=cover_letter,
            content_type="cover_letter",
            word_count=len(cover_letter.split()),
            suggestions=[
                "Customize the highlighted achievements for each application",
                "Research the company to add specific details",
                "Keep the letter to one page",
            ],
        )
    
    def optimize_resume_bullets(
        self,
        original_bullets: List[str],
        target_role: str = None,
    ) -> List[Dict[str, str]]:
        """
        Optimize resume bullet points for impact.
        
        Args:
            original_bullets: Original bullet points
            target_role: Target role to optimize for
        """
        logger.info(f"Optimizing {len(original_bullets)} resume bullets")
        
        optimized = []
        
        for bullet in original_bullets:
            # Apply optimization rules
            improved = self._optimize_bullet(bullet)
            
            optimized.append({
                "original": bullet,
                "optimized": improved,
                "changes": self._get_bullet_changes(bullet, improved),
            })
        
        return optimized
    
    def _optimize_bullet(self, bullet: str) -> str:
        """Optimize a single bullet point."""
        improved = bullet
        
        # Start with action verb if not already
        weak_starts = ["responsible for", "helped", "worked on", "assisted with"]
        strong_verbs = ["Led", "Developed", "Implemented", "Achieved", "Designed", "Built"]
        
        bullet_lower = bullet.lower()
        for weak in weak_starts:
            if bullet_lower.startswith(weak):
                # Replace with strong verb
                import random
                verb = random.choice(strong_verbs)
                improved = f"{verb} {bullet[len(weak):].strip()}"
                break
        
        # Capitalize first letter
        if improved and not improved[0].isupper():
            improved = improved[0].upper() + improved[1:]
        
        # Add period if missing
        if improved and not improved.endswith('.'):
            improved += '.'
        
        return improved
    
    def _get_bullet_changes(self, original: str, improved: str) -> List[str]:
        """Describe changes made to bullet point."""
        changes = []
        
        if original.lower() != improved.lower():
            if original.lower().startswith(("responsible for", "helped", "worked on")):
                changes.append("Replaced weak start with action verb")
            if improved.endswith('.') and not original.endswith('.'):
                changes.append("Added proper punctuation")
            if improved[0].isupper() and not original[0].isupper():
                changes.append("Capitalized properly")
        
        if not changes:
            changes.append("Already well-formatted")
        
        return changes
    
    def generate_linkedin_summary(
        self,
        current_role: str,
        skills: List[str],
        experience_years: float,
        interests: List[str] = None,
        achievements: List[str] = None,
    ) -> GeneratedContent:
        """
        Generate a LinkedIn profile summary.
        
        Args:
            current_role: Current job title
            skills: Key skills
            experience_years: Years of experience
            interests: Professional interests
            achievements: Notable achievements
        """
        logger.info("Generating LinkedIn summary")
        
        skills_text = ", ".join(skills[:6]) if skills else "various technologies"
        interests_text = " and ".join(interests[:3]) if interests else "technology"
        
        summary = f"""Experienced {current_role} with {experience_years:.0f}+ years of expertise in {skills_text}.

I am passionate about {interests_text} and building solutions that make a real impact. Throughout my career, I have focused on delivering high-quality work while continuously learning and growing.

{self._format_achievements(achievements)}

I'm always interested in connecting with fellow professionals and exploring new opportunities. Feel free to reach out!

📧 Open to discussing: New opportunities, collaborations, and industry insights"""

        return GeneratedContent(
            content=summary,
            content_type="linkedin_summary",
            word_count=len(summary.split()),
            suggestions=[
                "Add specific metrics and achievements",
                "Include industry-specific keywords for searchability",
                "Keep it under 2000 characters",
                "Update regularly with new accomplishments",
            ],
        )
    
    def _format_achievements(self, achievements: List[str]) -> str:
        """Format achievements for display."""
        if not achievements:
            return """Key highlights:
✓ Delivered projects that improved efficiency and user satisfaction
✓ Collaborated with cross-functional teams to achieve business goals
✓ Mentored team members and contributed to a positive team culture"""
        
        lines = ["Key highlights:"]
        for ach in achievements[:4]:
            lines.append(f"✓ {ach}")
        
        return "\n".join(lines)
    
    def generate_professional_summary(
        self,
        skills: List[str],
        experience_years: float,
        current_role: str,
        target_role: str = None,
    ) -> GeneratedContent:
        """
        Generate a professional summary for resume.
        
        Args:
            skills: Key skills
            experience_years: Years of experience
            current_role: Current position
            target_role: Target position (optional)
        """
        skills_text = ", ".join(skills[:5]) if skills else "relevant technical skills"
        
        if target_role and target_role.lower() != current_role.lower():
            summary = f"""Results-driven {current_role} with {experience_years:.0f}+ years of experience seeking to transition into {target_role}. Proven expertise in {skills_text}. Passionate about continuous learning and delivering impactful solutions. Strong combination of technical skills and business acumen."""
        else:
            summary = f"""Results-driven {current_role} with {experience_years:.0f}+ years of experience specializing in {skills_text}. Proven track record of delivering high-quality solutions and collaborating effectively with cross-functional teams. Committed to continuous improvement and staying current with industry best practices."""

        return GeneratedContent(
            content=summary,
            content_type="professional_summary",
            word_count=len(summary.split()),
            suggestions=[
                "Tailor the summary for each job application",
                "Include 1-2 specific achievements with metrics",
                "Keep it to 3-4 sentences",
            ],
        )
    
    def generate_skill_description(
        self,
        skill: str,
        proficiency_level: int = 3,  # 1-5 scale
        context: str = None,
    ) -> GeneratedContent:
        """
        Generate a description of skill proficiency.
        
        Args:
            skill: Skill name
            proficiency_level: Proficiency (1-5)
            context: Additional context (e.g., projects, years)
        """
        level_descriptions = {
            1: "Basic understanding",
            2: "Working knowledge with some hands-on experience",
            3: "Proficient with solid practical experience",
            4: "Advanced expertise with extensive project work",
            5: "Expert-level mastery with deep knowledge",
        }
        
        level_text = level_descriptions.get(proficiency_level, level_descriptions[3])
        
        description = f"{skill}: {level_text}."
        if context:
            description += f" {context}"
        
        return GeneratedContent(
            content=description,
            content_type="skill_description",
            word_count=len(description.split()),
            suggestions=[
                "Add specific projects or achievements using this skill",
                "Include any certifications or formal training",
            ],
        )


# Singleton instance
_generator_instance: Optional[ContentGenerator] = None


def get_content_generator() -> ContentGenerator:
    """Get or create singleton ContentGenerator instance."""
    global _generator_instance
    if _generator_instance is None:
        _generator_instance = ContentGenerator()
    return _generator_instance
