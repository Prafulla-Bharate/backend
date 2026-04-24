"""
Career Services
===============
Business logic for career-related operations.

SIMPLIFIED ARCHITECTURE:
1. ML Model: Fast initial career prediction with confidence
2. Gemini AI: Single call to verify/enrich with salary, skills, trends
3. Fallback: If Gemini fails, return ML predictions only (graceful degradation)
"""

import logging
import re
from typing import Any, Dict, List, Optional

from apps.career.models import (
    CareerPath,
    CareerPrediction,
)

from services.ml.career_model_v2 import get_career_prediction_model
ML_MODELS_AVAILABLE = True

logger = logging.getLogger(__name__)


def _canonical_title(title: str) -> str:
    cleaned = re.sub(r"\s+", " ", str(title or "")).strip()
    lower = cleaned.lower()
    aliases = {
        "node.js developer": "Node.js Developer",
        "full stack developer": "Full Stack Developer",
        "frontend developer": "Frontend Developer",
        "backend developer": "Backend Developer",
        "data scientist": "Data Scientist",
        "data engineer": "Data Engineer",
        "data analyst": "Data Analyst",
        "ml engineer": "ML Engineer",
        "ai research engineer": "AI Research Engineer",
        "devops engineer": "DevOps Engineer",
        "cloud engineer": "Cloud Engineer",
        "android developer": "Android Developer",
        "ios developer": "iOS Developer",
        "qa engineer": "QA Engineer",
        "business analyst": "Business Analyst",
        "product manager": "Product Manager",
        "ui/ux designer": "UI/UX Designer",
        "cybersecurity engineer": "Cybersecurity Engineer",
        "embedded engineer": "Embedded Engineer",
        "game developer": "Game Developer",
        "java developer": "Java Developer",
        "python developer": "Python Developer",
        "solution architect": "Solution Architect",
        "technical lead": "Technical Lead",
        "database administrator": "Database Administrator",
        "network engineer": "Network Engineer",
        "systems administrator": "Systems Administrator",
        "technical writer": "Technical Writer",
        "salesforce developer": "Salesforce Developer",
        "erp consultant": "ERP Consultant",
    }
    return aliases.get(lower, cleaned.title())


def _career_family(title: str) -> str:
    lower = _canonical_title(title).lower()
    if any(key in lower for key in ["data scientist", "data engineer", "data analyst", "ml engineer", "ai research"]):
        return "data"
    if any(key in lower for key in ["devops", "cloud"]):
        return "cloud"
    if any(key in lower for key in ["cybersecurity", "security"]):
        return "security"
    if any(key in lower for key in ["android", "ios", "mobile"]):
        return "mobile"
    if any(key in lower for key in ["ui/ux", "designer"]):
        return "design"
    if any(key in lower for key in ["qa", "test"]):
        return "qa"
    if any(key in lower for key in ["product manager", "business analyst"]):
        return "product"
    if any(key in lower for key in ["solution architect", "technical lead"]):
        return "leadership"
    if any(key in lower for key in ["database administrator", "network engineer", "systems administrator"]):
        return "infrastructure"
    if any(key in lower for key in ["technical writer"]):
        return "writer"
    if any(key in lower for key in ["salesforce", "erp"]):
        return "enterprise"
    if any(key in lower for key in ["game", "embedded"]):
        return "specialized"
    return "software"


def _career_reference(title: str) -> Dict[str, Any]:
    canonical = _canonical_title(title)
    family = _career_family(canonical)

    family_profiles = {
        "software": {
            "salary_range": {"min": 600000, "max": 1800000, "currency": "INR"},
            "salary_progression": {"entry": 600000, "mid": 1200000, "senior": 1800000},
            "job_openings": 65000,
            "demand_level": "High",
            "demand_trend": "rising",
            "industry_growth": 16,
            "growth_potential": "14% projected growth",
            "top_companies": ["TCS", "Infosys", "Wipro", "Accenture", "Capgemini"],
            "top_locations": ["Bangalore", "Hyderabad", "Pune", "Chennai", "Remote"],
            "trends": {"current": "Strong hiring for product and service teams.", "future": "Demand is shifting toward cloud-native and AI-assisted delivery.", "technologies": ["Cloud", "APIs", "AI tools"]},
            "career_path_roles": {"entry_roles": ["Junior Developer", "Associate Engineer"], "mid_roles": ["Software Engineer", "Senior Developer"], "senior_roles": ["Lead Engineer", "Engineering Manager"], "time_to_senior": "4-7 years"},
            "skills_to_develop": ["System design", "Testing", "Cloud basics", "Database design", "Git workflows"],
            "required_skills": ["Programming fundamentals", "SQL", "APIs", "Problem solving", "Debugging"],
            "success_factors": ["Ship features reliably", "Write maintainable code", "Communicate clearly"],
            "challenges": ["Fast-changing stack choices", "Balancing speed with quality"],
            "day_in_life": "Build features, fix bugs, review pull requests, and collaborate with product and design teams.",
        },
        "data": {
            "salary_range": {"min": 800000, "max": 2600000, "currency": "INR"},
            "salary_progression": {"entry": 800000, "mid": 1600000, "senior": 2600000},
            "job_openings": 42000,
            "demand_level": "High",
            "demand_trend": "rising",
            "industry_growth": 18,
            "growth_potential": "18% projected growth",
            "top_companies": ["Amazon", "Flipkart", "Fractal", "Mu Sigma", "Tredence"],
            "top_locations": ["Bangalore", "Hyderabad", "Mumbai", "Pune", "Remote"],
            "trends": {"current": "Analytics and ML roles remain in demand across industries.", "future": "More focus on applied AI, data platforms, and decision intelligence.", "technologies": ["Python", "SQL", "BI tools", "ML", "Cloud data platforms"]},
            "career_path_roles": {"entry_roles": ["Data Analyst", "Junior Data Scientist"], "mid_roles": ["Data Scientist", "Data Engineer"], "senior_roles": ["Lead Data Scientist", "Analytics Manager"], "time_to_senior": "4-6 years"},
            "skills_to_develop": ["Statistics", "SQL", "Python", "Machine learning", "Data storytelling"],
            "required_skills": ["Python", "SQL", "Statistics", "Visualization", "Business understanding"],
            "success_factors": ["Work with real datasets", "Explain findings clearly", "Build strong experimentation habits"],
            "challenges": ["Data quality issues", "Getting business buy-in"],
            "day_in_life": "Clean datasets, build dashboards or models, and translate analysis into business decisions.",
        },
        "cloud": {
            "salary_range": {"min": 900000, "max": 3000000, "currency": "INR"},
            "salary_progression": {"entry": 900000, "mid": 1800000, "senior": 3000000},
            "job_openings": 28000,
            "demand_level": "High",
            "demand_trend": "rising",
            "industry_growth": 17,
            "growth_potential": "17% projected growth",
            "top_companies": ["AWS", "Microsoft", "Google", "Cisco", "TCS"],
            "top_locations": ["Bangalore", "Hyderabad", "Pune", "Gurugram", "Remote"],
            "trends": {"current": "Cloud migration and DevOps are standard across teams.", "future": "Platform engineering and automation will keep expanding.", "technologies": ["AWS", "Azure", "Kubernetes", "Terraform", "CI/CD"]},
            "career_path_roles": {"entry_roles": ["Cloud Engineer", "DevOps Engineer"], "mid_roles": ["Senior DevOps Engineer", "Cloud Architect"], "senior_roles": ["Principal Cloud Architect", "Platform Lead"], "time_to_senior": "5-8 years"},
            "skills_to_develop": ["Linux", "Docker", "Kubernetes", "Terraform", "Monitoring"],
            "required_skills": ["Linux", "Networking", "Cloud platforms", "Automation", "CI/CD"],
            "success_factors": ["Automate repeatable work", "Understand reliability", "Learn incident response"],
            "challenges": ["Operational responsibility", "Keeping up with cloud services"],
            "day_in_life": "Maintain deployments, automate infrastructure, and improve reliability for application teams.",
        },
        "security": {
            "salary_range": {"min": 1000000, "max": 3200000, "currency": "INR"},
            "salary_progression": {"entry": 1000000, "mid": 1900000, "senior": 3200000},
            "job_openings": 24000,
            "demand_level": "High",
            "demand_trend": "rising",
            "industry_growth": 16,
            "growth_potential": "16% projected growth",
            "top_companies": ["Palo Alto Networks", "Microsoft", "Amazon", "Cognizant", "TCS"],
            "top_locations": ["Bangalore", "Hyderabad", "Pune", "Gurugram", "Remote"],
            "trends": {"current": "Security teams are being expanded across product and enterprise orgs.", "future": "More demand for cloud security, SOC, and threat hunting.", "technologies": ["SIEM", "Cloud security", "IAM", "Threat detection", "Zero trust"]},
            "career_path_roles": {"entry_roles": ["Security Analyst", "SOC Analyst"], "mid_roles": ["Security Engineer", "Incident Responder"], "senior_roles": ["Principal Security Engineer", "Security Architect"], "time_to_senior": "5-8 years"},
            "skills_to_develop": ["Networking", "Threat analysis", "Linux", "SIEM", "Incident response"],
            "required_skills": ["Networking", "Linux", "Security fundamentals", "Risk analysis", "Scripting"],
            "success_factors": ["Stay current on threats", "Practice labs regularly", "Understand defensive controls"],
            "challenges": ["High stakes work", "Constantly evolving threat landscape"],
            "day_in_life": "Monitor alerts, investigate incidents, and strengthen systems against threats.",
        },
        "mobile": {
            "salary_range": {"min": 700000, "max": 2400000, "currency": "INR"},
            "salary_progression": {"entry": 700000, "mid": 1400000, "senior": 2400000},
            "job_openings": 18000,
            "demand_level": "Medium",
            "demand_trend": "stable",
            "industry_growth": 13,
            "growth_potential": "13% projected growth",
            "top_companies": ["Google", "Swiggy", "Zomato", "Byju's", "Infosys"],
            "top_locations": ["Bangalore", "Hyderabad", "Pune", "Chennai", "Remote"],
            "trends": {"current": "Mobile apps remain key for consumer products.", "future": "Cross-platform and performance-focused apps are growing.", "technologies": ["Kotlin", "Swift", "Flutter", "React Native"]},
            "career_path_roles": {"entry_roles": ["Mobile Developer", "Associate App Developer"], "mid_roles": ["Senior Android/iOS Developer"], "senior_roles": ["Mobile Lead", "Mobile Architect"], "time_to_senior": "4-7 years"},
            "skills_to_develop": ["Platform APIs", "State management", "Testing", "Performance tuning", "App publishing"],
            "required_skills": ["Kotlin/Swift", "UI design", "API integration", "Debugging", "Version control"],
            "success_factors": ["Ship stable releases", "Optimize performance", "Understand platform guidelines"],
            "challenges": ["Platform fragmentation", "App store policy changes"],
            "day_in_life": "Implement mobile features, resolve crashes, and collaborate with backend and design teams.",
        },
        "design": {
            "salary_range": {"min": 600000, "max": 2200000, "currency": "INR"},
            "salary_progression": {"entry": 600000, "mid": 1200000, "senior": 2200000},
            "job_openings": 14000,
            "demand_level": "Medium",
            "demand_trend": "stable",
            "industry_growth": 12,
            "growth_potential": "12% projected growth",
            "top_companies": ["Google", "Adobe", "Amazon", "Figma", "Flipkart"],
            "top_locations": ["Bangalore", "Mumbai", "Delhi", "Pune", "Remote"],
            "trends": {"current": "Product teams are investing more in user experience.", "future": "Systems thinking and AI-assisted workflows will matter more.", "technologies": ["Figma", "Design systems", "Prototyping", "Accessibility"]},
            "career_path_roles": {"entry_roles": ["UI Designer", "UX Associate"], "mid_roles": ["Product Designer", "UX Designer"], "senior_roles": ["Lead Designer", "Design Manager"], "time_to_senior": "5-8 years"},
            "skills_to_develop": ["Interaction design", "Design systems", "Research", "Accessibility", "Prototyping"],
            "required_skills": ["UI/UX principles", "Figma", "Research", "Communication", "Usability"],
            "success_factors": ["Solve user problems", "Create clean interfaces", "Validate with feedback"],
            "challenges": ["Balancing user and business needs", "Communicating design value"],
            "day_in_life": "Sketch flows, design interfaces, and collaborate with product managers and engineers.",
        },
        "qa": {
            "salary_range": {"min": 500000, "max": 1500000, "currency": "INR"},
            "salary_progression": {"entry": 500000, "mid": 900000, "senior": 1500000},
            "job_openings": 22000,
            "demand_level": "Medium",
            "demand_trend": "stable",
            "industry_growth": 9,
            "growth_potential": "9% projected growth",
            "top_companies": ["TCS", "Infosys", "Accenture", "Capgemini", "Cognizant"],
            "top_locations": ["Bangalore", "Pune", "Hyderabad", "Chennai", "Remote"],
            "trends": {"current": "Automation coverage is expected in most quality teams.", "future": "Test engineering and reliability skills are becoming more valuable.", "technologies": ["Selenium", "Playwright", "API testing", "CI/CD"]},
            "career_path_roles": {"entry_roles": ["QA Engineer", "Test Engineer"], "mid_roles": ["Senior QA Engineer", "Automation Engineer"], "senior_roles": ["QA Lead", "Quality Manager"], "time_to_senior": "4-7 years"},
            "skills_to_develop": ["Automation", "Test design", "API testing", "CI/CD", "Bug tracking"],
            "required_skills": ["Attention to detail", "Test planning", "Automation basics", "API testing", "Communication"],
            "success_factors": ["Find bugs early", "Automate high-value cases", "Document clearly"],
            "challenges": ["Manual work can dominate", "Keeping test suites reliable"],
            "day_in_life": "Design tests, run automation, and validate releases before they go live.",
        },
        "product": {
            "salary_range": {"min": 1000000, "max": 3000000, "currency": "INR"},
            "salary_progression": {"entry": 1000000, "mid": 1800000, "senior": 3000000},
            "job_openings": 18000,
            "demand_level": "High",
            "demand_trend": "rising",
            "industry_growth": 14,
            "growth_potential": "14% projected growth",
            "top_companies": ["Google", "Amazon", "Flipkart", "Microsoft", "Zomato"],
            "top_locations": ["Bangalore", "Mumbai", "Delhi", "Gurugram", "Remote"],
            "trends": {"current": "Product and business roles are blending more with analytics.", "future": "AI product thinking and platform strategy will be important.", "technologies": ["Analytics", "Roadmapping", "A/B testing", "AI product tools"]},
            "career_path_roles": {"entry_roles": ["Business Analyst", "Associate Product Manager"], "mid_roles": ["Product Manager", "Senior Business Analyst"], "senior_roles": ["Group Product Manager", "Product Lead"], "time_to_senior": "5-8 years"},
            "skills_to_develop": ["Stakeholder management", "Analytics", "Roadmapping", "Experimentation", "Communication"],
            "required_skills": ["Problem framing", "Communication", "Analytics", "Product sense", "Prioritization"],
            "success_factors": ["Understand customer problems", "Make data-backed decisions", "Align teams"],
            "challenges": ["Ambiguous responsibilities", "Balancing speed and strategy"],
            "day_in_life": "Define priorities, review metrics, and coordinate engineers, design, and leadership.",
        },
        "leadership": {
            "salary_range": {"min": 1500000, "max": 3500000, "currency": "INR"},
            "salary_progression": {"entry": 1500000, "mid": 2500000, "senior": 3500000},
            "job_openings": 10000,
            "demand_level": "High",
            "demand_trend": "stable",
            "industry_growth": 12,
            "growth_potential": "12% projected growth",
            "top_companies": ["Google", "Microsoft", "Amazon", "Infosys", "TCS"],
            "top_locations": ["Bangalore", "Hyderabad", "Pune", "Mumbai", "Remote"],
            "trends": {"current": "System design and team leadership are in constant demand.", "future": "Cross-functional leadership and platform thinking will grow.", "technologies": ["System design", "Architecture", "Leadership", "Cloud"]},
            "career_path_roles": {"entry_roles": ["Senior Engineer"], "mid_roles": ["Tech Lead", "Solution Architect"], "senior_roles": ["Engineering Manager", "Director of Engineering"], "time_to_senior": "6-10 years"},
            "skills_to_develop": ["System design", "Mentoring", "Architecture", "Communication", "Planning"],
            "required_skills": ["Leadership", "System design", "Architecture", "Mentoring", "Decision making"],
            "success_factors": ["Balance technical and people leadership", "Drive execution", "Communicate clearly"],
            "challenges": ["Broad accountability", "Managing ambiguity"],
            "day_in_life": "Review architecture, unblock teams, and guide technical direction.",
        },
        "infrastructure": {
            "salary_range": {"min": 500000, "max": 1800000, "currency": "INR"},
            "salary_progression": {"entry": 500000, "mid": 1000000, "senior": 1800000},
            "job_openings": 15000,
            "demand_level": "Medium",
            "demand_trend": "stable",
            "industry_growth": 8,
            "growth_potential": "8% projected growth",
            "top_companies": ["IBM", "TCS", "Infosys", "Wipro", "HCL"],
            "top_locations": ["Bangalore", "Pune", "Chennai", "Hyderabad", "Remote"],
            "trends": {"current": "Operations teams are automating more work.", "future": "Infrastructure roles will shift toward cloud and platform operations.", "technologies": ["Linux", "Networking", "Monitoring", "Automation"]},
            "career_path_roles": {"entry_roles": ["System Administrator", "Support Engineer"], "mid_roles": ["Senior SysAdmin", "Network Engineer"], "senior_roles": ["Infrastructure Lead", "IT Operations Manager"], "time_to_senior": "5-8 years"},
            "skills_to_develop": ["Linux", "Networking", "Monitoring", "Scripting", "Troubleshooting"],
            "required_skills": ["Linux", "Networking", "Troubleshooting", "Automation", "Monitoring"],
            "success_factors": ["Keep systems reliable", "Document procedures", "Automate repetitive tasks"],
            "challenges": ["On-call pressure", "Legacy systems"],
            "day_in_life": "Handle system uptime, monitor alerts, and support deployments and users.",
        },
        "writer": {
            "salary_range": {"min": 400000, "max": 1200000, "currency": "INR"},
            "salary_progression": {"entry": 400000, "mid": 750000, "senior": 1200000},
            "job_openings": 6000,
            "demand_level": "Medium",
            "demand_trend": "stable",
            "industry_growth": 7,
            "growth_potential": "7% projected growth",
            "top_companies": ["Atlassian", "Microsoft", "Google", "Notion", "Freshworks"],
            "top_locations": ["Bangalore", "Remote", "Pune", "Hyderabad", "Mumbai"],
            "trends": {"current": "Documentation is valued more in product and platform teams.", "future": "API documentation and developer education will stay important.", "technologies": ["Docs tooling", "Markdown", "API specs", "Research"]},
            "career_path_roles": {"entry_roles": ["Technical Writer", "Documentation Specialist"], "mid_roles": ["Senior Technical Writer", "Content Strategist"], "senior_roles": ["Documentation Lead", "Developer Education Manager"], "time_to_senior": "4-7 years"},
            "skills_to_develop": ["Research", "API understanding", "Editing", "Information architecture", "Audience writing"],
            "required_skills": ["Writing", "Research", "Clarity", "Technical understanding", "Organization"],
            "success_factors": ["Write for a specific audience", "Keep content accurate", "Work closely with engineers"],
            "challenges": ["Keeping docs current", "Explaining complex systems simply"],
            "day_in_life": "Research products, write and update docs, and collaborate with subject-matter experts.",
        },
        "enterprise": {
            "salary_range": {"min": 700000, "max": 2200000, "currency": "INR"},
            "salary_progression": {"entry": 700000, "mid": 1400000, "senior": 2200000},
            "job_openings": 9000,
            "demand_level": "Medium",
            "demand_trend": "stable",
            "industry_growth": 10,
            "growth_potential": "10% projected growth",
            "top_companies": ["Salesforce", "Oracle", "SAP", "Infosys", "TCS"],
            "top_locations": ["Bangalore", "Hyderabad", "Pune", "Gurugram", "Remote"],
            "trends": {"current": "Enterprise platforms remain a strong niche skillset.", "future": "Integration and automation around enterprise platforms will increase.", "technologies": ["Salesforce", "Apex", "Workflow automation", "Integrations"]},
            "career_path_roles": {"entry_roles": ["Salesforce Developer", "ERP Associate"], "mid_roles": ["Senior Salesforce Developer", "ERP Consultant"], "senior_roles": ["Solution Architect", "Platform Lead"], "time_to_senior": "5-8 years"},
            "skills_to_develop": ["Platform configuration", "Apex", "Integration", "Business process understanding", "Testing"],
            "required_skills": ["CRM understanding", "Configuration", "Apex", "Integration", "Problem solving"],
            "success_factors": ["Understand business workflows", "Build reliable automations", "Keep systems scalable"],
            "challenges": ["Working with legacy processes", "Customizations creating complexity"],
            "day_in_life": "Customize enterprise workflows, build integrations, and support business teams.",
        },
        "specialized": {
            "salary_range": {"min": 700000, "max": 2600000, "currency": "INR"},
            "salary_progression": {"entry": 700000, "mid": 1500000, "senior": 2600000},
            "job_openings": 12000,
            "demand_level": "Medium",
            "demand_trend": "stable",
            "industry_growth": 11,
            "growth_potential": "11% projected growth",
            "top_companies": ["Ubisoft", "EA", "Samsung", "Bosch", "Intel"],
            "top_locations": ["Bangalore", "Pune", "Hyderabad", "Chennai", "Remote"],
            "trends": {"current": "Game and embedded roles are niche but steady.", "future": "Specialized hardware and immersive product development will remain niche areas.", "technologies": ["C++", "Embedded systems", "Game engines", "RTOS"]},
            "career_path_roles": {"entry_roles": ["Game Developer", "Embedded Engineer"], "mid_roles": ["Senior Game/Embedded Engineer"], "senior_roles": ["Lead Engineer", "Systems Architect"], "time_to_senior": "5-8 years"},
            "skills_to_develop": ["C/C++", "Debugging", "Performance tuning", "Hardware or engine concepts", "Systems thinking"],
            "required_skills": ["C/C++", "Algorithms", "Debugging", "Systems knowledge", "Problem solving"],
            "success_factors": ["Build reliable systems", "Optimize performance", "Learn domain-specific tooling"],
            "challenges": ["Smaller market size", "High domain depth required"],
            "day_in_life": "Write low-level code, debug hard problems, and optimize for performance or hardware constraints.",
        },
    }

    return {
        "title": canonical,
        "family": family,
        **family_profiles[family],
    }


def _profile_fit_score(user_profile: Dict[str, Any], reference: Dict[str, Any], ml_confidence: float) -> float:
    skills = {str(s).strip().lower() for s in user_profile.get("skills", []) if s}
    required = {str(s).strip().lower() for s in reference.get("required_skills", []) if s}
    matched = len(skills & required)
    skill_ratio = matched / max(len(required), 1)

    experience_years = float(user_profile.get("experience_years", 0) or 0)
    level = reference.get("family")
    if level in {"leadership"}:
        experience_score = 1.0 if experience_years >= 5 else 0.6 if experience_years >= 2 else 0.3
    elif level in {"senior", "cloud", "security", "data", "product", "enterprise"}:
        experience_score = 1.0 if experience_years >= 3 else 0.7 if experience_years >= 1 else 0.35
    else:
        experience_score = 1.0 if experience_years >= 0.5 else 0.75

    degree = str(user_profile.get("education", [{}])[0].get("degree_type", "") if user_profile.get("education") else "").lower()
    field = str(user_profile.get("education", [{}])[0].get("field_of_study", "") if user_profile.get("education") else "").lower()
    education_score = 1.0
    if any(word in field for word in ["computer", "software", "it", "data", "electronics", "electrical"]):
        education_score = 1.0
    elif degree in {"diploma"}:
        education_score = 0.7

    score = (0.55 * float(ml_confidence or 0) + 0.3 * skill_ratio + 0.1 * experience_score + 0.05 * education_score)
    return max(0.35, min(score, 0.96))


def _build_reasoning(user_profile: Dict[str, Any], reference: Dict[str, Any], matched_skills: list[str]) -> str:
    skills_text = ", ".join(matched_skills[:3]) if matched_skills else "your current profile"
    role = user_profile.get("current_role") or "your background"
    experience_years = user_profile.get("experience_years", 0) or 0
    return (
        f"This role fits because your profile aligns with {skills_text}. "
        f"With {experience_years} years of experience and a {reference['family']} profile, "
        f"it is a realistic next step from {role}."
    )


class CareerPredictionService:
    """Service for AI career predictions."""
    
    @staticmethod
    def get_latest_prediction(user) -> Optional[CareerPrediction]:
        """Get the most recent prediction for a user."""
        return CareerPrediction.objects.filter(
            user=user,
            status=CareerPrediction.PredictionStatus.COMPLETED,
            deleted_at__isnull=True
        ).order_by("-created_at").first()
    
    @staticmethod
    def request_prediction(
        user,
        target_industries: Optional[List[str]] = None,
        target_roles: Optional[List[str]] = None,
        career_level: Optional[str] = None,
        location_preference: Optional[str] = None,
        salary_expectation: Optional[float] = None,
        timeline_years: int = 5
    ) -> CareerPrediction:
        """Request a new career prediction."""
        from django.conf import settings
        
        # Build input data snapshot
        input_data = {
            "target_industries": target_industries or [],
            "target_roles": target_roles or [],
            "career_level": career_level,
            "location_preference": location_preference,
            "salary_expectation": float(salary_expectation) if salary_expectation else None,
            "timeline_years": timeline_years,
            # Add user profile snapshot
            "user_profile": CareerPredictionService._get_user_profile_snapshot(user)
        }
        
        prediction = CareerPrediction.objects.create(
            user=user,
            input_data=input_data
        )
        
        # Run prediction synchronously
        try:
            CareerPredictionService.perform_prediction(prediction)
            prediction.refresh_from_db()
        except Exception as e:
            logger.warning(f"Prediction failed synchronously: {e}")
        return prediction
    
    @staticmethod
    def _get_user_profile_snapshot(user) -> Dict[str, Any]:
        """Get comprehensive snapshot of user profile for prediction. Ensures all values are JSON serializable (no Decimal)."""
        import logging
        from decimal import Decimal
        from datetime import date, datetime
        logger = logging.getLogger(__name__)

        def convert_decimal(obj):
            """Recursively convert non-JSON-serializable types in dicts/lists."""
            if isinstance(obj, Decimal):
                return float(obj)
            elif isinstance(obj, (datetime,)):
                return obj.isoformat()
            elif isinstance(obj, date):
                return obj.isoformat()
            elif isinstance(obj, dict):
                return {k: convert_decimal(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_decimal(i) for i in obj]
            else:
                return obj

        snapshot = {
            "skills": [],
            "experience_years": 0,
            "education": [],
            "current_role": None,
            "industry": None,
            "certifications": [],
            "projects": [],
            "languages": [],
            "interests": [],
            "achievements": [],
            "social_links": [],
        }
        # Skills
        if hasattr(user, "skills"):
            snapshot["skills"] = list(
                user.skills.select_related("skill").values_list("skill__name", flat=True)
            )
        # Experience
        if hasattr(user, "experiences"):
            experiences = user.experiences.all()
            if experiences.exists():
                current = experiences.filter(is_current=True).first()
                if current:
                    snapshot["current_role"] = current.job_title
                    snapshot["industry"] = current.company_industry
                total_months = sum(
                    exp.duration_months for exp in experiences if exp.duration_months is not None
                )
                snapshot["experience_years"] = round(total_months / 12, 1)
                # Add all achievements from experiences
                for exp in experiences:
                    if exp.achievements:
                        snapshot["achievements"].extend(exp.achievements)
        # Education
        if hasattr(user, "educations"):
            snapshot["education"] = list(
                user.educations.values(
                    "degree_type", "degree_name", "field_of_study", "institution_name", "gpa", "gpa_scale", "achievements", "location"
                )
            )
            # Add all achievements from education
            for edu in user.educations.all():
                if edu.achievements:
                    snapshot["achievements"].extend(edu.achievements)
        # Certifications
        if hasattr(user, "certifications"):
            snapshot["certifications"] = list(
                user.certifications.values(
                    "name", "issuing_organization", "issue_date", "expiry_date", "description", "related_skills__name"
                )
            )
        # Projects
        if hasattr(user, "projects"):
            snapshot["projects"] = list(
                user.projects.values(
                    "title", "description", "technologies", "achievements", "project_url", "repository_url", "start_date", "end_date"
                )
            )
        # Languages
        if hasattr(user, "languages"):
            snapshot["languages"] = list(
                user.languages.values(
                    "language_name", "language_code", "proficiency", "is_native"
                )
            )
        # Interests
        if hasattr(user, "interests"):
            snapshot["interests"] = list(
                user.interests.select_related("interest").values_list("interest__name", flat=True)
            )
        # Social Links
        if hasattr(user, "social_links"):
            snapshot["social_links"] = list(
                user.social_links.values("platform", "url", "username", "is_primary")
            )
        # Log missing/empty fields
        for key, value in snapshot.items():
            if not value:
                logger.warning(f"[Prediction] User profile field '{key}' is empty or missing for user {user}")
        # Convert all Decimal to float recursively
        snapshot = convert_decimal(snapshot)
        return snapshot
    
    @staticmethod
    def perform_prediction(prediction: CareerPrediction) -> CareerPrediction:
        import time

        start_time = time.time()
        prediction.status = CareerPrediction.PredictionStatus.PROCESSING
        prediction.save(update_fields=["status"])

        try:
            user_profile = prediction.input_data.get("user_profile", {})
            user_skills = [str(skill).strip() for skill in user_profile.get("skills", []) if skill]
            experience_years = float(user_profile.get("experience_years", 0) or 0)
            education = user_profile.get("education", []) or []
            current_role = str(user_profile.get("current_role", "") or "")
            industry = str(user_profile.get("industry", "") or "")
            target_industries = prediction.input_data.get("target_industries", [])
            target_roles = prediction.input_data.get("target_roles", [])
            career_level = prediction.input_data.get("career_level", "")
            location = prediction.input_data.get("location_preference", "India")
            salary_expectation = prediction.input_data.get("salary_expectation")
            timeline_years = prediction.input_data.get("timeline_years", 5)

            education_level = education[0].get("degree_type", "") if education else ""
            education_field = education[0].get("field_of_study", "") if education else ""

            ml_predictions: list[dict[str, Any]] = []
            ml_confidence = 0.0

            if ML_MODELS_AVAILABLE:
                try:
                    ml_model = get_career_prediction_model()
                    if ml_model.is_trained:
                        ml_profile = {
                            "skills": user_skills,
                            "experience_years": experience_years,
                            "current_job_title": current_role,
                            "education_degree": education_level or "bachelor",
                            "field_of_study": education_field or "",
                            "certifications": [
                                (c.get("name") or c.get("issuing_organization", "")) if isinstance(c, dict) else str(c)
                                for c in user_profile.get("certifications", [])
                                if c
                            ],
                            "industry": industry,
                        }
                        ml_output = ml_model.predict(ml_profile)
                        ml_confidence = float(ml_output.confidence or 0)
                        ml_predictions = ml_output.top_predictions[:5] if ml_output.top_predictions else []
                        if not ml_predictions and ml_output.predicted_career:
                            ml_predictions = [{"career": ml_output.predicted_career, "score": ml_confidence}]
                except Exception as exc:
                    logger.warning("ML prediction failed: %s", exc)

            if not ml_predictions:
                ml_predictions = [
                    {"career": "Backend Developer", "score": 0.55},
                    {"career": "Full Stack Developer", "score": 0.5},
                    {"career": "Data Analyst", "score": 0.45},
                ]

            recommended_careers: list[dict[str, Any]] = []
            for ml_pred in ml_predictions[:5]:
                title = _canonical_title(str(ml_pred.get("career", "")))
                reference = _career_reference(title)
                db_career = CareerPath.objects.filter(title__iexact=title).first() or CareerPath.objects.filter(title__icontains=title).first()

                required_skills = [str(s) for s in reference.get("required_skills", [])]
                matched_skills = [skill for skill in user_skills if any(token in skill.lower() for token in [req.lower() for req in required_skills])]
                skills_to_develop = [skill for skill in reference.get("skills_to_develop", []) if skill not in matched_skills][:5]
                final_score = _profile_fit_score(user_profile, reference, float(ml_pred.get("score", 0) or 0))

                salary_range = reference["salary_range"]
                salary_progression = reference["salary_progression"]
                reasoning = _build_reasoning(user_profile, reference, matched_skills)

                recommended_careers.append({
                    "career_id": str(db_career.id) if db_career else None,
                    "title": title,
                    "match_score": final_score,
                    "reasons": [reasoning],
                    "skills_matched": matched_skills,
                    "skills_to_develop": skills_to_develop,
                    "salary_range": salary_range,
                    "salary_progression": salary_progression,
                    "growth_rate": reference.get("industry_growth", 0),
                    "demand_score": 0.85,
                    "market_demand": reference.get("demand_level", "Medium"),
                    "demand_trend": reference.get("demand_trend", "stable"),
                    "industry_growth": reference.get("industry_growth", 0),
                    "growth_potential": reference.get("growth_potential", ""),
                    "top_companies": reference.get("top_companies", []),
                    "top_locations": reference.get("top_locations", []),
                    "trends": reference.get("trends", {}),
                    "career_path": [],
                    "career_path_roles": reference.get("career_path_roles", {}),
                    "job_openings": int(reference.get("job_openings", 0)),
                    "success_factors": reference.get("success_factors", []),
                    "challenges": reference.get("challenges", []),
                    "day_in_life": reference.get("day_in_life", ""),
                    "source": "ml_v2_fast",
                })

            top_reference = _career_reference(recommended_careers[0]["title"])
            top_salary = top_reference["salary_range"]
            top_progression = top_reference["salary_progression"]

            prediction.recommended_careers = recommended_careers
            prediction.current_career_assessment = {
                "summary": (
                    f"Your profile is a practical fit for {recommended_careers[0]['title']}. "
                    f"The recommendation is based on your skills, {experience_years} years of experience, and your current profile signals."
                ),
                "strengths": user_skills[:5],
                "areas_for_improvement": recommended_careers[0]["skills_to_develop"][:5],
            }
            prediction.skill_gaps = recommended_careers[0]["skills_to_develop"][:5]
            prediction.recommended_skills = recommended_careers[0]["skills_to_develop"][:5]
            prediction.salary_projection = {
                "current_market_rate": top_salary,
                "expected_in_5_years": {
                    "min": int(top_progression["mid"]),
                    "max": int(top_progression["senior"]),
                    "currency": "INR",
                },
                "factors_affecting_salary": ["experience", "skill depth", "location", "company size"],
            }
            prediction.status = CareerPrediction.PredictionStatus.COMPLETED
            prediction.confidence_score = max(0.35, min(float(ml_confidence or 0.5), 0.96))
            prediction.model_used = "ml_v2_fast"
            prediction.processing_time_ms = int((time.time() - start_time) * 1000)

        except Exception as exc:
            prediction.status = CareerPrediction.PredictionStatus.FAILED
            prediction.error_message = str(exc)
            logger.error("Prediction failed: %s", exc, exc_info=True)

        prediction.save()
        return prediction
    
