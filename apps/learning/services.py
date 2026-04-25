"""
Learning Services
=================
Business logic for learning-related operations.
Uses centralized ML services and Gemini AI for recommendations.

ADAPTIVE LEARNING INTEGRATION:
- Quiz completion triggers adaptive engine
- Project submissions reviewed by AI
- Certificate verification
- Skill mastery tracking with decay
"""

import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from datetime import timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from django.conf import settings
from django.db import transaction
from django.db.models import Avg, Count, F, Q, Sum
from django.utils import timezone

from apps.learning.models import (
    LearningPath,
    LearningPhase,
    LearningResource,
    UserLearningPathEnrollment,
    UserResourceProgress,
    KnowledgeCheckpoint,
    UserCheckpointAttempt,
    RecommendedResource,
    # New adaptive models
    UserSkillMastery,
    PhaseInjection,
    ProjectSubmission,
    CertificateVerification,
    SkillRefresherQuiz,
    LearningPathUpdate,
)

# Import centralized ML and AI services
from services import get_learning_recommender, get_skill_matcher
from services.ai.prompts import AIPromptsService

logger = logging.getLogger(__name__)


class LearningPathService:
    """Service for learning path operations."""

    @staticmethod
    def _build_role_requirements(target_role: str, target_career=None) -> Dict[str, Any]:
        """Build role-specific, industry-relevant requirements used to steer path generation."""
        role = (target_role or "").lower()

        requirements: Dict[str, Any] = {
            "must_have_skills": [
                "Git", "Linux", "SQL", "API Integration", "Testing", "Debugging",
                "Security Fundamentals", "System Design", "Cloud Basics", "CI/CD",
                "Monitoring & Logging", "Communication",
            ],
            "must_have_tools": [
                "GitHub", "VS Code", "Postman", "Docker", "GitHub Actions",
                "AWS/GCP/Azure", "Sentry/Grafana",
            ],
            "trend_topics": [
                "AI-assisted development workflows",
                "Cloud-native deployment",
                "Observability and reliability",
                "Secure-by-default engineering",
            ],
            "industry_workflows": [
                "Translate business requirements into technical tasks",
                "Ship features with tests and monitoring",
                "Review code and collaborate via pull requests",
                "Debug production issues with logs and metrics",
            ],
        }

        role_overrides = [
            (
                ["data scientist", "data science", "machine learning", "ml", "ai engineer", "genai", "nlp"],
                {
                    "must_have_skills": [
                        "Python", "Statistics", "Linear Algebra", "SQL", "Data Wrangling",
                        "Data Visualization", "Machine Learning", "Model Evaluation", "Feature Engineering",
                        "MLOps", "LLMs", "Prompt Engineering", "RAG", "Experiment Tracking",
                    ],
                    "must_have_tools": [
                        "Pandas", "NumPy", "Scikit-learn", "PyTorch/TensorFlow", "Jupyter",
                        "MLflow/Weights & Biases", "Docker", "FastAPI", "Airflow", "BigQuery/Snowflake",
                    ],
                    "trend_topics": [
                        "LLM application architecture (RAG, evals, guardrails)",
                        "Model serving and inference optimization",
                        "Feature stores and data quality contracts",
                        "Responsible AI and model governance",
                    ],
                },
            ),
            (
                ["full stack", "fullstack", "web developer", "software engineer"],
                {
                    "must_have_skills": [
                        "HTML", "CSS", "JavaScript", "TypeScript", "React", "Backend APIs",
                        "Authentication", "Databases", "Caching", "Testing", "System Design",
                        "Performance Optimization", "Security", "CI/CD", "Cloud Deployment",
                    ],
                    "must_have_tools": [
                        "React", "Node.js/Django", "PostgreSQL", "Redis", "Docker",
                        "GitHub Actions", "Vercel/Render", "Nginx", "Playwright/Cypress",
                    ],
                    "trend_topics": [
                        "Server-side rendering and edge delivery",
                        "API-first architecture and typed contracts",
                        "Performance budgets and Core Web Vitals",
                        "Containerized full-stack deployment",
                    ],
                },
            ),
            (
                ["backend", "api", "server"],
                {
                    "must_have_skills": [
                        "API Design", "Database Design", "Authentication", "Authorization",
                        "Caching", "Asynchronous Processing", "Testing", "Observability",
                        "Security", "Scalability", "Incident Debugging",
                    ],
                    "must_have_tools": [
                        "Django/FastAPI/Node", "PostgreSQL", "Redis", "Celery", "Docker",
                        "Kubernetes", "Prometheus/Grafana", "Sentry", "Nginx",
                    ],
                    "trend_topics": [
                        "Event-driven systems and queue-based architecture",
                        "Zero-downtime deployments",
                        "API rate limiting and resilience patterns",
                        "SLO-based reliability engineering",
                    ],
                },
            ),
            (
                ["frontend", "ui", "react"],
                {
                    "must_have_skills": [
                        "HTML", "CSS", "JavaScript", "TypeScript", "React", "State Management",
                        "Accessibility", "Frontend Testing", "Performance Optimization", "API Integration",
                        "Design Systems", "Debugging",
                    ],
                    "must_have_tools": [
                        "React", "Vite", "Tailwind", "Redux/Zustand", "Jest/Vitest", "Playwright",
                        "Storybook", "Lighthouse", "Sentry",
                    ],
                    "trend_topics": [
                        "Web performance engineering",
                        "Accessible component architecture",
                        "Design token driven UI systems",
                        "AI-assisted UX and frontend workflows",
                    ],
                },
            ),
            (
                ["devops", "sre", "cloud engineer", "platform engineer"],
                {
                    "must_have_skills": [
                        "Linux", "Networking", "Infrastructure as Code", "Containers", "Kubernetes",
                        "CI/CD", "Monitoring", "Incident Response", "Security Hardening", "Cost Optimization",
                    ],
                    "must_have_tools": [
                        "Terraform", "Docker", "Kubernetes", "GitHub Actions/Jenkins",
                        "Prometheus", "Grafana", "ELK", "AWS/GCP/Azure",
                    ],
                    "trend_topics": [
                        "Platform engineering and internal developer platforms",
                        "Policy-as-code and supply chain security",
                        "FinOps and cloud cost governance",
                        "Progressive delivery and canary strategies",
                    ],
                },
            ),
        ]

        for keywords, override in role_overrides:
            if any(keyword in role for keyword in keywords):
                for key, values in override.items():
                    merged = list(dict.fromkeys([*(requirements.get(key) or []), *(values or [])]))
                    requirements[key] = merged
                break

        if target_career:
            required_skills = list(getattr(target_career, "required_skills", []) or [])
            preferred_skills = list(getattr(target_career, "preferred_skills", []) or [])
            certifications = list(getattr(target_career, "certifications", []) or [])
            requirements["must_have_skills"] = list(
                dict.fromkeys([
                    *(requirements.get("must_have_skills") or []),
                    *required_skills,
                    *preferred_skills,
                ])
            )
            if certifications:
                requirements["trend_topics"] = list(
                    dict.fromkeys([
                        *(requirements.get("trend_topics") or []),
                        f"Certification alignment: {', '.join(str(c) for c in certifications[:5])}",
                    ])
                )

        requirements["must_have_skills"] = requirements.get("must_have_skills", [])[:30]
        requirements["must_have_tools"] = requirements.get("must_have_tools", [])[:20]
        requirements["trend_topics"] = requirements.get("trend_topics", [])[:10]
        requirements["industry_workflows"] = requirements.get("industry_workflows", [])[:8]
        return requirements

    @staticmethod
    def _infer_role_family(target_role: str) -> str:
        role = (target_role or "").lower()
        if any(k in role for k in [
            "machine learning", "ml ", " ai", "ai ", "data scientist", "data science",
            "llm", "nlp", "computer vision", "data engineer", "analytics", "genai"
        ]):
            return "ai_data"
        if any(k in role for k in ["full stack", "fullstack", "web developer", "application developer"]):
            return "fullstack"
        if any(k in role for k in ["frontend", "front-end", "ui developer", "react developer"]):
            return "frontend"
        if any(k in role for k in ["backend", "back-end", "api developer", "server-side"]):
            return "backend"
        if any(k in role for k in ["devops", "sre", "site reliability", "platform engineer", "cloud engineer"]):
            return "devops"
        return "software"

    @staticmethod
    def _mandatory_phase_blueprints(role_family: str) -> List[Dict[str, Any]]:
        common_end = [
            {
                "title": "System Design, Scalability & Reliability",
                "keywords": ["system design", "scalability", "performance", "distributed", "reliability"],
                "skills": ["System Design", "Scalability", "Caching", "Load Balancing", "Observability"],
                "topics": ["High-level design", "Scaling patterns", "Caching", "Rate limiting", "Reliability patterns"],
            },
            {
                "title": "Cloud, Deployment & DevOps",
                "keywords": ["cloud", "deployment", "devops", "ci/cd", "docker", "kubernetes"],
                "skills": ["Docker", "CI/CD", "Cloud", "Infrastructure Basics", "Deployment"],
                "topics": ["Containerization", "CI/CD pipelines", "Cloud services", "Release strategy", "Rollback"],
            },
            {
                "title": "Security, Testing & Quality Engineering",
                "keywords": ["security", "testing", "quality", "qa", "jwt", "owasp"],
                "skills": ["Testing", "Security", "Code Quality", "Debugging", "Automation"],
                "topics": ["Unit/integration testing", "Auth & authz", "OWASP basics", "Static checks", "Regression testing"],
            },
            {
                "title": "Portfolio, Interview Prep & Career Launch",
                "keywords": ["portfolio", "interview", "resume", "career", "job"],
                "skills": ["Portfolio", "Interviewing", "Communication", "Project Storytelling", "Career Strategy"],
                "topics": ["Portfolio projects", "Interview patterns", "Resume/LinkedIn", "Mock interviews", "Job targeting"],
            },
        ]

        if role_family == "ai_data":
            return [
                {
                    "title": "Foundations: Python, Math, Statistics & Git",
                    "keywords": ["python", "math", "statistics", "git", "foundation"],
                    "skills": ["Python", "Linear Algebra", "Probability", "Statistics", "Git"],
                    "topics": ["Python essentials", "Probability", "Statistics", "Linear algebra", "Git workflow"],
                },
                {
                    "title": "Data Engineering Fundamentals (SQL, ETL, Warehousing)",
                    "keywords": ["sql", "etl", "warehouse", "data pipeline", "modeling"],
                    "skills": ["SQL", "Data Modeling", "ETL", "Data Warehousing", "Data Quality"],
                    "topics": ["Advanced SQL", "Data modeling", "ETL patterns", "Data quality", "Batch vs stream"],
                },
                {
                    "title": "Machine Learning Core",
                    "keywords": ["machine learning", "supervised", "unsupervised", "model evaluation"],
                    "skills": ["ML", "Feature Engineering", "Model Evaluation", "Experimentation"],
                    "topics": ["Supervised learning", "Unsupervised learning", "Feature engineering", "Cross-validation", "Error analysis"],
                },
                {
                    "title": "Deep Learning, NLP, LLMs & RAG",
                    "keywords": ["deep learning", "nlp", "llm", "rag", "transformers"],
                    "skills": ["Deep Learning", "Transformers", "LLMs", "RAG", "Prompt Engineering"],
                    "topics": ["Neural networks", "Transformers", "Prompting", "Embeddings", "RAG pipelines"],
                },
            ] + common_end

        if role_family == "fullstack":
            return [
                {
                    "title": "Web Foundations (HTML, CSS, JavaScript, Git)",
                    "keywords": ["html", "css", "javascript", "git", "web fundamentals"],
                    "skills": ["HTML", "CSS", "JavaScript", "Git", "Debugging"],
                    "topics": ["Semantic HTML", "CSS layouts", "JS fundamentals", "DOM", "Git workflow"],
                },
                {
                    "title": "Modern Frontend Engineering",
                    "keywords": ["react", "frontend", "state", "routing", "typescript"],
                    "skills": ["React", "TypeScript", "State Management", "Routing", "Frontend Testing"],
                    "topics": ["Components", "State patterns", "Routing", "Performance", "Accessibility"],
                },
                {
                    "title": "Backend APIs, Auth & Integrations",
                    "keywords": ["backend", "api", "rest", "auth", "jwt"],
                    "skills": ["Backend", "REST APIs", "Authentication", "Authorization", "API Design"],
                    "topics": ["API architecture", "Auth flows", "Validation", "Error handling", "Integrations"],
                },
                {
                    "title": "Databases, Caching & Data Access Patterns",
                    "keywords": ["database", "sql", "nosql", "redis", "orm"],
                    "skills": ["SQL", "NoSQL", "ORM", "Caching", "Query Optimization"],
                    "topics": ["Schema design", "Indexes", "Transactions", "Caching", "Data migrations"],
                },
            ] + common_end

        # Generic software default
        return [
            {
                "title": "Programming & Computer Science Foundations",
                "keywords": ["programming", "foundation", "data structures", "algorithms"],
                "skills": ["Programming", "Data Structures", "Algorithms", "Git"],
                "topics": ["Core syntax", "Data structures", "Algorithms", "Complexity", "Version control"],
            },
            {
                "title": "Application Development Core Stack",
                "keywords": ["application", "backend", "frontend", "apis"],
                "skills": ["Application Architecture", "APIs", "Frontend/Backend Basics"],
                "topics": ["Architecture", "APIs", "Data flow", "Validation", "Error handling"],
            },
        ] + common_end

    @staticmethod
    def _build_default_resources(phase_title: str, target_role: str) -> List[Dict[str, Any]]:
        topic = phase_title.replace("Phase", "").strip()
        return [
            {
                "title": f"{topic} - Official Documentation",
                "type": "documentation",
                "provider": "Docs",
                "search_query": f"official documentation {topic} {target_role}",
                "is_free": True,
                "description": "Canonical documentation for accurate concepts and APIs.",
            },
            {
                "title": f"{topic} - Practical Video Course",
                "type": "video",
                "provider": "YouTube",
                "search_query": f"{topic} complete course 2025 {target_role}",
                "is_free": True,
                "description": "Hands-on video walkthrough to build practical understanding.",
            },
            {
                "title": f"{topic} - Guided Practice",
                "type": "practice",
                "provider": "GitHub",
                "search_query": f"{topic} exercises projects {target_role}",
                "is_free": True,
                "description": "Practice set to reinforce concepts with implementation.",
            },
            {
                "title": f"{topic} - Project Build",
                "type": "project",
                "provider": "GitHub",
                "search_query": f"{topic} production project example {target_role}",
                "is_free": True,
                "description": "Project-oriented learning to demonstrate real-world readiness.",
            },
        ]

    @staticmethod
    def _build_structured_fallback_path(
        target_role: str,
        role_family: str,
        total_hours: int,
        experience_level: str,
        current_skills: Optional[List[str]] = None,
        skills_to_learn: Optional[List[str]] = None,
        role_requirements: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a fast, deterministic, and realistic path when AI generation is slow/unavailable."""
        blueprints = list(LearningPathService._mandatory_phase_blueprints(role_family))
        current_skills = current_skills or []
        skills_to_learn = skills_to_learn or []
        role_requirements = role_requirements or {}
        requirement_skills = [
            str(s).strip()
            for s in (role_requirements.get("must_have_skills") or [])
            if str(s).strip()
        ]
        requirement_tools = [
            str(s).strip()
            for s in (role_requirements.get("must_have_tools") or [])
            if str(s).strip()
        ]
        trend_topics = [
            str(s).strip()
            for s in (role_requirements.get("trend_topics") or [])
            if str(s).strip()
        ]

        supplemental = [
            {
                "title": "Professional Collaboration & Product Thinking",
                "skills": ["Communication", "Stakeholder Management", "Product Thinking", "Documentation"],
                "topics": ["Requirement analysis", "Decision logs", "Team communication", "Delivery planning", "Feedback loops"],
            },
            {
                "title": "Industry Tools & Current Technology Stack",
                "skills": requirement_skills[:6] or ["Industry Tooling", "Workflow Automation"],
                "topics": (requirement_tools[:6] + trend_topics[:3])[:8] or [
                    "Toolchain setup", "Versioned workflows", "Automation hooks", "Quality gates", "Release readiness"
                ],
            },
            {
                "title": "Interview Excellence & Portfolio Storytelling",
                "skills": ["Interview Preparation", "Portfolio Presentation", "Behavioral Answers", "Case Practice"],
                "topics": ["Mock interviews", "Project storytelling", "STAR framework", "Role targeting", "Offer-readiness"],
            },
        ]

        phase_templates = blueprints + supplemental
        while len(phase_templates) < 10:
            idx = len(phase_templates) + 1
            focus = skills_to_learn[(idx - 1) % len(skills_to_learn)] if skills_to_learn else f"{target_role} Practice"
            phase_templates.append({
                "title": f"Applied Project Sprint: {focus}",
                "skills": [focus, "Execution", "Problem Solving", "Debugging"],
                "topics": ["End-to-end implementation", "Trade-off analysis", "Performance tuning", "Edge-case handling", "Production checklist"],
            })

        phase_templates = phase_templates[:12]
        phase_count = len(phase_templates)
        hours_per_phase = max(8, int(total_hours / max(phase_count, 1)))

        phases: List[Dict[str, Any]] = []
        for i, template in enumerate(phase_templates, start=1):
            progress = i / max(phase_count, 1)
            if progress <= 0.35:
                difficulty = LearningPath.DifficultyLevel.BEGINNER
            elif progress <= 0.7:
                difficulty = LearningPath.DifficultyLevel.INTERMEDIATE
            elif progress <= 0.9:
                difficulty = LearningPath.DifficultyLevel.ADVANCED
            else:
                difficulty = LearningPath.DifficultyLevel.EXPERT

            skills = [s for s in template.get("skills", []) if s][:8]
            prioritized_skills = list(dict.fromkeys([*skills_to_learn, *requirement_skills]))
            if prioritized_skills:
                for skill in prioritized_skills[:8]:
                    if skill not in skills and len(skills) < 8:
                        skills.append(skill)

            phases.append({
                "title": f"Phase {i}: {template.get('title', 'Career Development Module')}",
                "description": (
                    f"Structured training module for {target_role} focused on practical execution, "
                    "real-world constraints, and measurable outcomes."
                ),
                "skills_covered": skills,
                "topics_covered": template.get("topics", [])[:8],
                "learning_objectives": [
                    f"Build production-ready competency in {skills[0] if skills else 'core role skills'}",
                    "Complete hands-on implementation with clear quality standards",
                    "Demonstrate outcomes through documented project artifacts",
                ],
                "prerequisite_skills": current_skills[:4] if i == 1 else [],
                "readiness_checklist": [
                    "Can explain key concepts and trade-offs confidently",
                    "Can implement the core workflow without guided help",
                    "Can debug and validate the solution using realistic test scenarios",
                ],
                "resources": LearningPathService._build_default_resources(template.get("title", target_role), target_role),
                "estimated_hours": hours_per_phase,
                "difficulty": difficulty,
                "phase_outcome": f"Ready to apply {template.get('title', 'this phase')} in job-like tasks.",
            })

        all_skills = set(skills_to_learn or [])
        for phase in phases:
            all_skills.update(phase.get("skills_covered", []))

        return {
            "title": f"Industry-Ready Roadmap to {target_role}",
            "description": (
                f"A complete and practical path to become job-ready as a {target_role}. "
                "This roadmap balances fundamentals, production workflows, and interview readiness."
            ),
            "difficulty": experience_level or LearningPath.DifficultyLevel.INTERMEDIATE,
            "total_hours": sum(int(p.get("estimated_hours", 0) or 0) for p in phases),
            "skills_covered": list(all_skills)[:80],
            "phases": phases,
        }

    @staticmethod
    def _strengthen_recommendations(
        recommendations: Dict[str, Any],
        target_role: str,
        total_hours: int,
        experience_level: str,
        skills_to_learn: Optional[List[str]] = None,
        role_requirements: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Harden AI output into an end-to-end, industry-ready path.

        Ensures: minimum phase coverage, mandatory production topics, complete phase shape,
        and realistic hours distribution.
        """
        result = dict(recommendations or {})
        phases = list(result.get("phases") or [])
        role_requirements = role_requirements or {}
        requirement_skills = [
            str(s).strip()
            for s in (role_requirements.get("must_have_skills") or [])
            if str(s).strip()
        ]
        requirement_tools = [
            str(s).strip()
            for s in (role_requirements.get("must_have_tools") or [])
            if str(s).strip()
        ]
        trend_topics = [
            str(s).strip()
            for s in (role_requirements.get("trend_topics") or [])
            if str(s).strip()
        ]
        industry_workflows = [
            str(s).strip()
            for s in (role_requirements.get("industry_workflows") or [])
            if str(s).strip()
        ]

        role_family = LearningPathService._infer_role_family(target_role)
        blueprints = LearningPathService._mandatory_phase_blueprints(role_family)

        def _phase_text_blob(phase: Dict[str, Any]) -> str:
            bits = [
                str(phase.get("title", "")),
                str(phase.get("description", "")),
                " ".join(phase.get("topics_covered", []) or []),
                " ".join(phase.get("skills_covered", []) or []),
            ]
            return " ".join(bits).lower()

        existing_blob = "\n".join(_phase_text_blob(p) for p in phases)
        missing_blueprints: List[Dict[str, Any]] = []
        for bp in blueprints:
            if not any(k.lower() in existing_blob for k in bp.get("keywords", [])):
                missing_blueprints.append(bp)

        for bp in missing_blueprints:
            phases.append({
                "title": bp["title"],
                "description": f"Industry-ready coverage of {bp['title']} for {target_role}.",
                "skills_covered": bp.get("skills", []),
                "topics_covered": bp.get("topics", []),
                "learning_objectives": [
                    f"Build practical proficiency in {bp.get('skills', ['core skills'])[0]}",
                    f"Apply {bp['title']} concepts to production scenarios",
                    "Deliver a verifiable project artifact for portfolio readiness",
                ],
                "prerequisite_skills": [],
                "readiness_checklist": [
                    "Can you explain the core concepts without looking up references?",
                    "Can you implement a practical solution from scratch?",
                    "Can you troubleshoot common production issues independently?",
                ],
                "resources": LearningPathService._build_default_resources(bp["title"], target_role),
                "estimated_hours": max(8, int(total_hours / 10)),
            })

        if requirement_tools or trend_topics:
            phase_blob = "\n".join(_phase_text_blob(p) for p in phases)
            has_tools_phase = any(
                token.lower() in phase_blob
                for token in [*requirement_tools[:8], "tooling", "workflow", "stack"]
            )
            if not has_tools_phase:
                phases.append({
                    "title": "Industry Tooling, Trends & Delivery Workflows",
                    "description": f"Practical tooling and modern workflow alignment for {target_role} based on current hiring expectations.",
                    "skills_covered": (requirement_skills[:4] + ["Delivery Workflow", "Operational Excellence"])[:8],
                    "topics_covered": (requirement_tools[:6] + trend_topics[:4])[:10] or [
                        "Production toolchain", "Workflow automation", "Release process", "Observability setup"
                    ],
                    "learning_objectives": [
                        "Set up and use the core industry toolchain for daily delivery",
                        "Apply trend-aligned practices in practical implementation work",
                        "Ship features using modern team workflows and quality gates",
                    ],
                    "prerequisite_skills": [],
                    "readiness_checklist": [
                        "Can you execute the end-to-end delivery workflow independently?",
                        "Can you choose tools based on team and system constraints?",
                        "Can you troubleshoot pipeline and deployment failures quickly?",
                    ],
                    "resources": LearningPathService._build_default_resources("Industry tooling and workflows", target_role),
                    "estimated_hours": max(8, int(total_hours / 12)),
                })

        # Ensure robust phase count for end-to-end depth
        min_phase_count = 10
        if len(phases) < min_phase_count:
            for idx in range(min_phase_count - len(phases)):
                phases.append({
                    "title": f"Phase {len(phases) + 1}: Advanced Applied Practice {idx + 1}",
                    "description": f"Applied, production-oriented practice module for {target_role}.",
                    "skills_covered": (skills_to_learn or ["Advanced Practice"])[:4],
                    "topics_covered": [
                        "Production implementation",
                        "Performance tuning",
                        "Failure handling",
                        "Operational best practices",
                    ],
                    "learning_objectives": [
                        "Build production-grade implementations",
                        "Optimize reliability and performance",
                        "Document architecture and trade-offs clearly",
                    ],
                    "readiness_checklist": [
                        "Can you ship this independently?",
                        "Can you defend design decisions in a review?",
                        "Can you monitor and debug production behavior?",
                    ],
                    "resources": LearningPathService._build_default_resources("Advanced applied practice", target_role),
                    "estimated_hours": max(8, int(total_hours / 12)),
                })

        # Normalize each phase shape and difficulty progression
        valid_difficulties = [c[0] for c in LearningPath.DifficultyLevel.choices]
        total_phases = len(phases)
        for index, phase in enumerate(phases):
            phase.setdefault("title", f"Phase {index + 1}")
            phase.setdefault("description", f"Comprehensive module for {target_role}.")

            phase_skills = phase.get("skills_covered") or []
            if not isinstance(phase_skills, list):
                phase_skills = [str(phase_skills)]
            phase["skills_covered"] = [str(s).strip() for s in phase_skills if str(s).strip()][:10]

            topics = phase.get("topics_covered") or []
            if not isinstance(topics, list):
                topics = [str(topics)]
            normalized_topics = [str(t).strip() for t in topics if str(t).strip()]
            if industry_workflows:
                for workflow in industry_workflows[:4]:
                    if workflow not in normalized_topics and len(normalized_topics) < 10:
                        normalized_topics.append(workflow)
            phase["topics_covered"] = normalized_topics[:10] or [
                "Core concepts", "Hands-on implementation", "Production considerations", "Best practices"
            ]

            objectives = phase.get("learning_objectives") or []
            if not isinstance(objectives, list):
                objectives = [str(objectives)]
            objectives = [str(o).strip() for o in objectives if str(o).strip()]
            if len(objectives) < 3:
                objectives += [
                    f"Build practical competency in {phase['title']}",
                    "Implement production-minded solutions",
                    "Validate outcomes through projects and reviews",
                ]
            phase["learning_objectives"] = objectives[:3]

            checklist = phase.get("readiness_checklist") or []
            if not isinstance(checklist, list):
                checklist = [str(checklist)]
            checklist = [str(c).strip() for c in checklist if str(c).strip()]
            if len(checklist) < 3:
                checklist += [
                    "Can you complete the core implementation without guidance?",
                    "Can you explain trade-offs and constraints clearly?",
                    "Can you debug, test, and validate your solution end-to-end?",
                ]
            phase["readiness_checklist"] = checklist[:3]

            resources = phase.get("resources") or []
            if not isinstance(resources, list):
                resources = []
            if len(resources) < 4:
                resources = (resources + LearningPathService._build_default_resources(phase["title"], target_role))[:4]
            phase["resources"] = resources

            raw_hours = phase.get("estimated_hours", phase.get("hours", 0))
            try:
                raw_hours = int(raw_hours)
            except Exception:
                raw_hours = 0
            phase["estimated_hours"] = max(6, raw_hours)

            # Difficulty progression guardrail
            diff = str(phase.get("difficulty", "")).lower().strip()
            if diff not in valid_difficulties:
                progress = (index + 1) / max(total_phases, 1)
                if progress <= 0.35:
                    diff = LearningPath.DifficultyLevel.BEGINNER
                elif progress <= 0.7:
                    diff = LearningPath.DifficultyLevel.INTERMEDIATE
                elif progress <= 0.9:
                    diff = LearningPath.DifficultyLevel.ADVANCED
                else:
                    diff = LearningPath.DifficultyLevel.EXPERT
            phase["difficulty"] = diff

            phase["order"] = index + 1

        # Normalize total hours close to target hours
        hour_sum = sum(int(p.get("estimated_hours", 0) or 0) for p in phases)
        if hour_sum > 0:
            scale = float(max(total_hours, 80)) / float(hour_sum)
            for phase in phases:
                scaled = int(round((int(phase.get("estimated_hours", 0) or 0)) * scale))
                phase["estimated_hours"] = max(6, scaled)

            adjusted_sum = sum(int(p.get("estimated_hours", 0) or 0) for p in phases)
            delta = int(max(total_hours, 80) - adjusted_sum)
            if phases and delta != 0:
                phases[0]["estimated_hours"] = max(6, int(phases[0]["estimated_hours"]) + delta)

        result["phases"] = phases
        result["total_hours"] = sum(int(p.get("estimated_hours", 0) or 0) for p in phases)

        skills_union = set(result.get("skills_covered") or [])
        for phase in phases:
            for skill in phase.get("skills_covered", []) or []:
                if skill:
                    skills_union.add(skill)
        for skill in requirement_skills:
            skills_union.add(skill)
        result["skills_covered"] = list(skills_union)[:80]

        if not result.get("description"):
            result["description"] = f"End-to-end industry-ready roadmap for {target_role}, from fundamentals to expert production capability."
        if not result.get("difficulty"):
            result["difficulty"] = experience_level or LearningPath.DifficultyLevel.INTERMEDIATE

        return result
    
    @staticmethod
    def get_all_paths(
        difficulty: Optional[str] = None,
        category: Optional[str] = None,
        search: Optional[str] = None,
        is_featured: bool = False
    ):
        """Get filtered learning paths."""
        queryset = LearningPath.objects.filter(is_published=True)
        
        if difficulty:
            queryset = queryset.filter(difficulty=difficulty)
        
        if category:
            queryset = queryset.filter(category__iexact=category)
        
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(tags__contains=[search])
            )
        
        if is_featured:
            queryset = queryset.filter(is_featured=True)
        
        return queryset.prefetch_related("phases").order_by("-created_at")
    
    @staticmethod
    def get_path_by_slug(slug: str) -> Optional[LearningPath]:
        """Get learning path by slug."""
        try:
            return LearningPath.objects.prefetch_related(
                "phases__resources",
                "phases__checkpoints"
            ).get(slug=slug, is_published=True)
        except LearningPath.DoesNotExist:
            return None
    
    @staticmethod
    def get_recommended_paths(user, limit: int = 5) -> List[LearningPath]:
        """Get recommended learning paths for user."""
        # Get user's skills and interests
        from apps.profile.models import UserSkill, UserInterest
        
        user_skills = list(UserSkill.objects.filter(
            user=user
        ).values_list("name", flat=True))
        
        user_interests = list(UserInterest.objects.filter(
            user=user
        ).values_list("name", flat=True))
        
        # Already enrolled paths
        enrolled_ids = UserLearningPathEnrollment.objects.filter(
            user=user
        ).values_list("learning_path_id", flat=True)
        
        # Find paths matching interests but not enrolled
        paths = LearningPath.objects.filter(
            is_published=True
        ).exclude(
            id__in=enrolled_ids
        )
        
        # Prioritize by matching skills in prerequisites
        matching_paths = []
        for path in paths[:50]:  # Check first 50
            score = 0
            # Check if user has prerequisites
            for prereq in path.prerequisites:
                if prereq.lower() in [s.lower() for s in user_skills]:
                    score += 2
            
            # Check if path teaches skills user is interested in
            for skill in path.skills_covered:
                if skill.lower() in [i.lower() for i in user_interests]:
                    score += 1
            
            if score > 0:
                matching_paths.append((path, score))
        
        # Sort by score
        matching_paths.sort(key=lambda x: x[1], reverse=True)
        
        result = [p[0] for p in matching_paths[:limit]]
        
        # Fill with trending if not enough
        if len(result) < limit:
            trending = LearningPath.objects.filter(
                is_published=True,
                is_featured=True
            ).exclude(
                id__in=enrolled_ids
            ).exclude(
                id__in=[p.id for p in result]
            )[:limit - len(result)]
            result.extend(trending)
        
        return result
    
    @staticmethod
    def generate_personalized_path(
        user,
        target_career_id: Optional[UUID] = None,
        target_career_title: str = "",
        target_skills: List[str] = None,
        current_skills: List[str] = None,
        **options
    ) -> LearningPath:
        """
        Generate a personalized learning path using Gemini AI with a fault-tolerant pipeline.

        FAULT TOLERANCE STRATEGY
        ─────────────────────────
        Step 1  → Call LLM, capture raw JSON string immediately.
        Step 2  → Create LearningPath with raw_llm_response saved right away.
                  Even if later steps fail, the LLM output is never lost.
        Step 3  → Parse the saved raw text into phases/resources inside a
                  nested try/except — failures here don't lose the path record.
        Step 4  → If Gemini fails entirely, fall back to ML recommender.
        Step 5  → Last resort: minimal skeleton path.

        No quizzes / hardcoded URLs — both were the #1 cause of JSON parse failures
        and stale-link technical debt.  Resources use search_query instead.
        """
        import json as _json
        from apps.career.models import CareerPath

        # ── 1. Resolve target career ──────────────────────────────────────────
        target_career = None
        if target_career_id:
            try:
                target_career = CareerPath.objects.get(id=target_career_id)
            except CareerPath.DoesNotExist:
                pass
        if not target_career and target_career_title:
            # Try an exact or partial DB match; if none found, we still pass the
            # title string to the prompt so Gemini knows the target role.
            from django.db.models import Q as _Q
            target_career = CareerPath.objects.filter(
                _Q(title__iexact=target_career_title)
                | _Q(title__icontains=target_career_title),
                is_active=True,
            ).first()

        # ── 2. Collect current skills ─────────────────────────────────────────
        if not current_skills:
            from apps.profile.models import UserSkill
            current_skills = list(
                UserSkill.objects.filter(user=user).values_list("skill__name", flat=True)
            )

        # ── 3. Collect rich user profile context ──────────────────────────────
        user_context = LearningPathService._build_user_context(user)

        # ── 4. Collect existing skill mastery (skip already-expert skills) ────
        try:
            from apps.learning.models import UserSkillMastery
            expert_skills = list(
                UserSkillMastery.objects.filter(
                    user=user,
                    mastery_level__in=["expert", "proficient"],
                ).values_list("skill_name", flat=True)
            )
        except Exception:
            expert_skills = []

        # ── 5. Collect previously completed paths (avoid repeating content) ───
        try:
            completed_path_titles = list(
                UserLearningPathEnrollment.objects.filter(
                    user=user,
                    status=UserLearningPathEnrollment.EnrollmentStatus.COMPLETED,
                ).select_related("learning_path").values_list(
                    "learning_path__title", flat=True
                )
            )
        except Exception:
            completed_path_titles = []

        # ── 6. Compute skill gaps via ML matcher ──────────────────────────────
        learning_recommender = get_learning_recommender()
        skill_matcher = get_skill_matcher()

        target_skill_list = target_skills or []
        skill_gap_data: dict = {}
        if target_career and not target_skill_list:
            required_skills = target_career.required_skills or []
            if isinstance(required_skills, str):
                try:
                    required_skills = _json.loads(required_skills)
                except Exception:
                    required_skills = [s.strip() for s in required_skills.split(",")]
            try:
                gap_result = skill_matcher.get_skill_gaps(
                    current_skills=current_skills,
                    target_role=target_career.title,
                )
                skill_gap_data = gap_result
                target_skill_list = gap_result.get("prioritized_skills", required_skills)[:10]
            except Exception:
                target_skill_list = required_skills[:10]

        role_requirements = LearningPathService._build_role_requirements(
            target_role=(target_career.title if target_career else (target_career_title or "career growth")),
            target_career=target_career,
        )
        if not target_skill_list:
            target_skill_list = list(role_requirements.get("must_have_skills") or [])[:12]
        else:
            target_skill_list = list(dict.fromkeys([
                *target_skill_list,
                *(role_requirements.get("must_have_skills") or [])[:12],
            ]))

        # Remove skills user already has at expert/proficient level
        skills_to_learn = [s for s in target_skill_list if s not in expert_skills]

        # ── 7. Prepare generation options ──────────────────────────────────────
        target_role = (
            target_career.title
            if target_career
            else (target_career_title or "career growth")
        )
        experience_level = options.get("preferred_difficulty", "intermediate")
        weekly_hours = options.get("weekly_hours", 10)
        learning_style = options.get("learning_style", "mixed")
        timeline_weeks = options.get("timeline_weeks", 12)

        # ── 8. Call Gemini — capture raw text BEFORE any DB operation ────────
        raw_llm_text = ""
        recommendations: dict = {}
        model_used = "fallback_minimal"

        try:
            timeout_seconds = int(getattr(settings, "LEARNING_PATH_AI_TIMEOUT_SECONDS", 16))

            def _call_ai():
                ai_prompts = AIPromptsService()
                return ai_prompts.generate_learning_path(
                    career_goal=target_role,
                    target_role=target_role,
                    current_skills=current_skills,
                    skills_to_learn=skills_to_learn,
                    experience_level=experience_level,
                    hours_per_week=weekly_hours,
                    user_context=user_context,
                    expert_skills=expert_skills,
                    completed_paths=completed_path_titles,
                    learning_style=learning_style,
                    timeline_weeks=timeline_weeks,
                    role_requirements=role_requirements,
                )

            executor = ThreadPoolExecutor(max_workers=1)
            future = executor.submit(_call_ai)
            try:
                ai_result = future.result(timeout=timeout_seconds)
            finally:
                executor.shutdown(wait=False, cancel_futures=True)

            if ai_result and "error" not in ai_result:
                # Persist raw text immediately so it's never lost
                try:
                    raw_llm_text = _json.dumps(ai_result)
                except Exception:
                    raw_llm_text = str(ai_result)
                recommendations = {
                    "title": ai_result.get("title", ""),
                    "description": ai_result.get("description", ""),
                    "difficulty": ai_result.get("difficulty", experience_level),
                    "total_hours": ai_result.get("total_hours", weekly_hours * timeline_weeks),
                    "phases": ai_result.get("phases", []),
                }
                model_used = "gemini_1.5_pro + learning_recommender_v1.0"
            else:
                raise Exception(f"Gemini returned error or empty: {ai_result}")

        except FuturesTimeoutError:
            logger.warning(
                f"Gemini path generation timed out for user {user.id}; using structured fallback."
            )
            recommendations = LearningPathService._build_structured_fallback_path(
                target_role=target_role,
                role_family=LearningPathService._infer_role_family(target_role),
                total_hours=weekly_hours * timeline_weeks,
                experience_level=experience_level,
                current_skills=current_skills,
                skills_to_learn=skills_to_learn,
                role_requirements=role_requirements,
            )
            model_used = "structured_fallback_v2"

        except Exception as ai_error:
            logger.warning(f"Gemini path generation failed for user {user.id}: {ai_error}")
            recommendations = LearningPathService._build_structured_fallback_path(
                target_role=target_role,
                role_family=LearningPathService._infer_role_family(target_role),
                total_hours=weekly_hours * timeline_weeks,
                experience_level=experience_level,
                current_skills=current_skills,
                skills_to_learn=skills_to_learn,
                role_requirements=role_requirements,
            )
            model_used = "structured_fallback_v2"

        # ── 9. Build path title ───────────────────────────────────────────────
        target_total_hours = recommendations.get("total_hours") or (weekly_hours * timeline_weeks)
        try:
            target_total_hours = int(target_total_hours)
        except Exception:
            target_total_hours = weekly_hours * timeline_weeks

        recommendations = LearningPathService._strengthen_recommendations(
            recommendations=recommendations,
            target_role=target_role,
            total_hours=target_total_hours,
            experience_level=experience_level,
            skills_to_learn=skills_to_learn,
            role_requirements=role_requirements,
        )

        title = recommendations.get("title") or (
            f"Path to {target_career.title}" if target_career
            else f"Personalized Path for {user.first_name or user.email}"
        )

        # ── 10. Persist path — raw_llm_response saved here ───────────────────
        path = LearningPath.objects.create(
            title=title,
            description=recommendations.get("description", "AI-generated personalized learning path"),
            difficulty=recommendations.get(
                "difficulty",
                options.get("preferred_difficulty", LearningPath.DifficultyLevel.INTERMEDIATE),
            ),
            estimated_hours=recommendations.get("total_hours", 40),
            skills_covered=recommendations.get("skills_covered", skills_to_learn),
            prerequisites=current_skills[:10] if current_skills else [],
            is_ai_generated=True,
            ai_model_used=model_used,
            is_published=True,
            # Raw LLM output — never lost even if phase creation fails below
            raw_llm_response=raw_llm_text,
            skill_gap_analysis=skill_gap_data,
            generation_context={
                "target_role": target_role,
                "experience_level": experience_level,
                "weekly_hours": weekly_hours,
                "timeline_weeks": timeline_weeks,
                "skills_to_learn": skills_to_learn,
                "expert_skills": expert_skills,
                "role_requirements": role_requirements,
            },
        )

        # ── 11. Create phases and resources (fault-isolated) ─────────────────
        # If this block fails for any reason the path record (with raw LLM text)
        # is still saved. Users can retry without re-calling the LLM.
        try:
            type_mapping = {
                "article": LearningResource.ResourceType.ARTICLE,
                "video": LearningResource.ResourceType.VIDEO,
                "course": LearningResource.ResourceType.COURSE,
                "tutorial": LearningResource.ResourceType.TUTORIAL,
                "documentation": LearningResource.ResourceType.DOCUMENTATION,
                "book": LearningResource.ResourceType.BOOK,
                "project": LearningResource.ResourceType.PROJECT,
                "exercise": LearningResource.ResourceType.PRACTICE,
                "practice": LearningResource.ResourceType.PRACTICE,
            }
            provider_mapping = {
                "coursera": LearningResource.Provider.COURSERA,
                "udemy": LearningResource.Provider.UDEMY,
                "edx": LearningResource.Provider.EDEX,
                "youtube": LearningResource.Provider.YOUTUBE,
                "linkedin": LearningResource.Provider.LINKEDIN,
                "medium": LearningResource.Provider.MEDIUM,
                "github": LearningResource.Provider.GITHUB,
                "pluralsight": LearningResource.Provider.PLURALSIGHT,
                "freecodecamp": LearningResource.Provider.OTHER,
                "docs": LearningResource.Provider.OTHER,
            }

            phases_data = recommendations.get("phases", [])
            for i, phase_data in enumerate(phases_data):
                phase_difficulty = phase_data.get("difficulty", experience_level)
                # Normalise difficulty value
                if phase_difficulty not in [c[0] for c in LearningPath.DifficultyLevel.choices]:
                    phase_difficulty = LearningPath.DifficultyLevel.INTERMEDIATE

                phase = LearningPhase.objects.create(
                    learning_path=path,
                    title=phase_data.get("title", f"Phase {i + 1}"),
                    description=phase_data.get("description", ""),
                    order=i + 1,
                    estimated_hours=phase_data.get(
                        "estimated_hours",
                        phase_data.get("hours", phase_data.get("duration_hours", 10)),
                    ),
                    skills_covered=phase_data.get(
                        "skills_covered",
                        phase_data.get("skills", phase_data.get("skills_focus", [])),
                    ),
                    # Adaptive fields
                    learning_objectives=phase_data.get("learning_objectives", []),
                    prerequisite_skills=phase_data.get("prerequisite_skills", []),
                    difficulty=phase_difficulty,
                    # Rich content fields from LLM
                    capstone_project=phase_data.get("capstone_project", {}),
                    recommended_certifications=phase_data.get("recommended_certifications", []),
                    youtube_queries=phase_data.get("youtube_queries", []),
                    external_topics=phase_data.get("external_topics", []),
                    # New comprehensive fields
                    topics_covered=phase_data.get("topics_covered", []),
                    phase_outcome=phase_data.get("phase_outcome", ""),
                    readiness_checklist=phase_data.get("readiness_checklist", []),
                    interview_questions=phase_data.get("interview_questions", []),
                )

                resources_data = phase_data.get("resources", phase_data.get("learning_resources", []))
                for j, resource_data in enumerate(resources_data):
                    resource_type_str = resource_data.get("type", "article").lower()
                    provider_str = resource_data.get(
                        "provider", resource_data.get("platform", "")
                    ).lower()
                    provider_val = provider_mapping.get(provider_str, LearningResource.Provider.OTHER)

                    # Build URL: prefer explicit url if provided (fallback paths),
                    # otherwise build a search URL from search_query + provider
                    search_query = resource_data.get(
                        "search_query",
                        resource_data.get("title", ""),
                    )
                    stored_url = resource_data.get("url", "")
                    if not stored_url and search_query:
                        stored_url = LearningPathService._build_search_url(
                            provider_val, search_query
                        )

                    LearningResource.objects.create(
                        phase=phase,
                        title=resource_data.get("title", f"Resource {j + 1}"),
                        description=resource_data.get("description", ""),
                        resource_type=type_mapping.get(
                            resource_type_str, LearningResource.ResourceType.ARTICLE
                        ),
                        url=stored_url,
                        search_query=search_query,
                        difficulty=phase_difficulty,
                        order_in_phase=j + 1,
                        is_free=resource_data.get("is_free", True),
                        provider=provider_val,
                    )

        except Exception as phase_error:
            # Phases failed but path record with raw_llm_response is still intact
            logger.error(
                f"Phase/resource creation failed for path {path.id}: {phase_error}",
                exc_info=True,
            )

        if target_career:
            try:
                path.target_careers.add(target_career)
            except Exception:
                pass

        logger.info(
            f"Generated personalized path {path.id} for user {user.id} using {model_used}"
        )
        return path

    @staticmethod
    def _build_search_url(provider: str, search_query: str) -> str:
        """Build a provider-specific search URL from a search query.
        These base URLs are stable — platform search endpoints don't change.
        """
        from urllib.parse import quote_plus
        q = quote_plus(search_query)
        search_map = {
            "youtube": f"https://www.youtube.com/results?search_query={q}",
            "coursera": f"https://www.coursera.org/search?query={q}",
            "udemy": f"https://www.udemy.com/courses/search/?q={q}",
            "github": f"https://github.com/search?q={q}&type=repositories",
            "medium": f"https://medium.com/search?q={q}",
            "linkedin": f"https://www.linkedin.com/learning/search?keywords={q}",
            "pluralsight": f"https://www.pluralsight.com/search?q={q}",
            "edx": f"https://www.edx.org/search?q={q}",
        }
        return search_map.get(str(provider).lower(), f"https://www.google.com/search?q={q}")

    @staticmethod
    def generate_phase_deep_dive(phase: "LearningPhase", user) -> Dict[str, Any]:
        """
        Generate and cache a deep-dive curriculum for a single phase using Gemini.
        Called lazily from PhaseDetailView on first user click.
        Result is saved to phase.deep_dive_content so subsequent calls are instant.
        Returns the deep_dive_content dict.
        """
        import json as _json
        from django.utils import timezone as _tz

        try:
            from apps.profile.models import UserSkill
            current_skills = list(
                UserSkill.objects.filter(user=user).values_list("skill__name", flat=True)
            )[:15]
        except Exception:
            current_skills = []

        # Count total phases in this path
        total_phases = LearningPhase.objects.filter(
            learning_path=phase.learning_path
        ).count()

        # Get the career goal from path title
        career_goal = phase.learning_path.title

        try:
            ai_prompts = AIPromptsService()
            result = ai_prompts.generate_phase_deep_dive(
                phase_title=phase.title,
                phase_description=phase.description,
                career_goal=career_goal,
                skills_covered=phase.skills_covered or [],
                topics_covered=phase.topics_covered or [],
                difficulty=phase.difficulty,
                phase_order=phase.order,
                total_phases=total_phases,
                current_skills=current_skills,
            )
            if result and "error" not in result:
                phase.deep_dive_content = result
                phase.deep_dive_generated_at = _tz.now()
                # Also backfill topics_covered, interview_questions, readiness_checklist
                # if they weren't populated at path-generation time
                if not phase.topics_covered and result.get("topics"):
                    phase.topics_covered = [t.get("title", "") for t in result["topics"]]
                if not phase.interview_questions and result.get("interview_questions"):
                    phase.interview_questions = result["interview_questions"]
                if not phase.readiness_checklist and result.get("readiness_checklist"):
                    phase.readiness_checklist = result["readiness_checklist"]
                phase.save(update_fields=[
                    "deep_dive_content", "deep_dive_generated_at",
                    "topics_covered", "interview_questions", "readiness_checklist",
                ])
                logger.info(f"Generated deep-dive for phase {phase.id}")
                return result
            else:
                logger.warning(f"Deep-dive Gemini returned error for phase {phase.id}: {result}")
                return {}
        except Exception as e:
            logger.error(f"generate_phase_deep_dive failed for phase {phase.id}: {e}", exc_info=True)
            return {}

    @staticmethod
    def _build_user_context(user) -> Dict[str, Any]:
        """
        Collect all available user context to enrich Gemini prompt.
        Returns a dict safely — never raises.
        """
        ctx: Dict[str, Any] = {}
        try:
            from apps.profile.models import UserProfile
            profile = UserProfile.objects.get(user=user)
            ctx["experience_years"] = profile.experience_years or 0
            ctx["current_role"] = getattr(profile, "current_title", "") or ""
            ctx["education"] = getattr(profile, "education_level", "") or ""
            ctx["location"] = getattr(profile, "location", "") or ""
        except Exception:
            pass

        try:
            from apps.career.models import UserCareerGoal
            goals = list(
                UserCareerGoal.objects.filter(user=user, is_deleted=False)
                .select_related("target_career")
                .values_list("target_career__title", flat=True)
            )
            ctx["career_goals"] = goals
        except Exception:
            pass

        try:
            from apps.profile.models import UserSkill
            skill_data = list(
                UserSkill.objects.filter(user=user).values("name", "proficiency")
            )
            ctx["skill_proficiency"] = {
                s["name"]: s["proficiency"] for s in skill_data
            }
        except Exception:
            pass

        return ctx






class EnrollmentService:
    """Service for enrollment operations."""

    @staticmethod
    @transaction.atomic
    def enroll_user(
        user,
        learning_path: LearningPath,
        for_career=None
    ) -> UserLearningPathEnrollment:
        """Enroll user in a learning path."""
        enrollment, created = UserLearningPathEnrollment.objects.get_or_create(
            user=user,
            learning_path=learning_path,
            defaults={
                "status": UserLearningPathEnrollment.EnrollmentStatus.ENROLLED,
                "personalized_for_career": for_career
            }
        )
        
        if created:
            # Update path enrollment count
            learning_path.enrollments_count = F("enrollments_count") + 1
            learning_path.save(update_fields=["enrollments_count"])
            
            logger.info(
                f"User {user.id} enrolled in path {learning_path.id}"
            )
        
        return enrollment
    
    @staticmethod
    def get_user_enrollments(
        user,
        status: Optional[str] = None
    ):
        """Get user's enrollments."""
        queryset = (
            UserLearningPathEnrollment.objects.filter(user=user)
            .select_related("learning_path", "current_phase")
            .prefetch_related(
                "learning_path__phases",
                "learning_path__phases__resources",
                "learning_path__phases__checkpoints",
            )
            .order_by("-created_at")
        )

        if status:
            queryset = queryset.filter(status=status)

        return queryset
    
    @staticmethod
    @transaction.atomic
    def update_progress(
        enrollment: UserLearningPathEnrollment,
        phase_completed: Optional[UUID] = None,
    ):
        """
        Update enrollment progress.

        Uses hours-weighted completion so longer phases carry more weight (more
        accurate than counting phases equally).  Before marking a phase complete
        we verify on the server that all required checkpoints have been passed —
        this prevents the frontend-only gate from being bypassed.
        """
        enrollment.last_activity_at = timezone.now()

        if enrollment.status == UserLearningPathEnrollment.EnrollmentStatus.ENROLLED:
            enrollment.status = UserLearningPathEnrollment.EnrollmentStatus.IN_PROGRESS
            enrollment.started_at = timezone.now()

        if phase_completed:
            phase_id_str = str(phase_completed)
            if phase_id_str not in enrollment.completed_phases:
                # ── Server-side gate: all required checkpoints must be passed ──
                phase_obj = LearningPhase.objects.filter(id=phase_completed).first()
                if phase_obj:
                    required_checkpoints = phase_obj.checkpoints.filter(is_required=True)
                    all_passed = all(
                        UserCheckpointAttempt.objects.filter(
                            user=enrollment.user,
                            checkpoint=cp,
                            passed=True,
                        ).exists()
                        for cp in required_checkpoints
                    )
                    if not all_passed:
                        raise ValueError(
                            "You must pass all required checkpoints before "
                            "completing this phase."
                        )
                enrollment.completed_phases.append(phase_id_str)

        # ── Hours-weighted progress ───────────────────────────────────────────

            # ── Skill mastery boost for completed phase ───────────────────────────
            # This runs outside the `if phase_completed` block so it only fires
            # once per phase (we re-look up the phase object from what was just appended).
            try:
                if phase_completed and phase_obj and phase_obj.skills_covered:
                    for skill in phase_obj.skills_covered:
                        skill_name = str(skill).strip()
                        if not skill_name:
                            continue
                        mastery, _created = UserSkillMastery.objects.get_or_create(
                            user=enrollment.user,
                            skill_name=skill_name,
                            defaults={"mastery_score": 0},
                        )
                        # Phase completion gives a base boost capped at 100
                        mastery.mastery_score = min(100, mastery.mastery_score + 20)
                        mastery.record_verification(
                            verification_type="phase_completion",
                            score=65,
                            source=f"Phase: {phase_obj.title}",
                        )
                        mastery.save()
            except Exception as _e:
                logger.warning(f"Skill mastery update after phase completion failed: {_e}")

        all_phases = list(
            enrollment.learning_path.phases.values("id", "estimated_hours")
        )
        total_hours = sum(p["estimated_hours"] or 1 for p in all_phases) or 1
        completed_set = set(enrollment.completed_phases)
        completed_hours = sum(
            p["estimated_hours"] or 1
            for p in all_phases
            if str(p["id"]) in completed_set
        )
        enrollment.progress_percentage = min(100, int((completed_hours / total_hours) * 100))

        # ── Mark path complete ────────────────────────────────────────────────
        if enrollment.progress_percentage >= 100:
            enrollment.status = UserLearningPathEnrollment.EnrollmentStatus.COMPLETED
            enrollment.completed_at = timezone.now()
            enrollment.learning_path.completions_count = F("completions_count") + 1
            enrollment.learning_path.save(update_fields=["completions_count"])

        enrollment.save()
        return enrollment

    @staticmethod
    def get_next_phase(enrollment: UserLearningPathEnrollment) -> Optional[LearningPhase]:
        """Get next incomplete phase for the user."""
        phases = enrollment.learning_path.phases.order_by("order")
        for phase in phases:
            if str(phase.id) not in enrollment.completed_phases:
                return phase
        return None


class ResourceProgressService:
    """Service for resource progress tracking."""
    
    @staticmethod
    @transaction.atomic
    def update_progress(
        user,
        resource: LearningResource,
        enrollment: Optional[UserLearningPathEnrollment] = None,
        **data
    ) -> UserResourceProgress:
        """Update user's progress on a resource."""
        progress, created = UserResourceProgress.objects.get_or_create(
            user=user,
            resource=resource,
            defaults={"enrollment": enrollment}
        )
        
        if "status" in data:
            progress.status = data["status"]
            
            if data["status"] == UserResourceProgress.ProgressStatus.IN_PROGRESS:
                if not progress.started_at:
                    progress.started_at = timezone.now()
            
            elif data["status"] == UserResourceProgress.ProgressStatus.COMPLETED:
                progress.completed_at = timezone.now()
                progress.progress_percentage = 100
                
                # Update resource completion count
                resource.completions_count = F("completions_count") + 1
                resource.save(update_fields=["completions_count"])
        
        if "progress_percentage" in data:
            progress.progress_percentage = data["progress_percentage"]
        
        if "time_spent_minutes" in data:
            progress.time_spent_minutes += data["time_spent_minutes"]
            
            if enrollment:
                enrollment.total_time_spent_minutes += data["time_spent_minutes"]
                enrollment.save(update_fields=["total_time_spent_minutes"])
        
        if "notes" in data:
            progress.notes = data["notes"]
        
        if "is_bookmarked" in data:
            progress.is_bookmarked = data["is_bookmarked"]
        
        if "rating" in data:
            progress.rating = data["rating"]
        
        progress.save()
        
        # Check if phase is completed
        if progress.status == UserResourceProgress.ProgressStatus.COMPLETED:
            ResourceProgressService._check_phase_completion(
                user, resource.phase, enrollment
            )
        
        return progress
    
    @staticmethod
    def _check_phase_completion(
        user,
        phase: Optional[LearningPhase],
        enrollment: Optional[UserLearningPathEnrollment]
    ):
        """Check if all resources in phase are completed."""
        if not phase or not enrollment:
            return
        
        total_resources = phase.resources.count()
        completed = UserResourceProgress.objects.filter(
            user=user,
            resource__phase=phase,
            status=UserResourceProgress.ProgressStatus.COMPLETED
        ).count()
        
        if completed >= total_resources:
            # Check if all checkpoints passed
            checkpoints = phase.checkpoints.filter(is_required=True)
            all_passed = all(
                UserCheckpointAttempt.objects.filter(
                    user=user,
                    checkpoint=cp,
                    passed=True
                ).exists()
                for cp in checkpoints
            )
            
            if all_passed:
                EnrollmentService.update_progress(enrollment, phase.id)
    
    @staticmethod
    def get_user_bookmarks(user) -> List[UserResourceProgress]:
        """Get user's bookmarked resources."""
        return UserResourceProgress.objects.filter(
            user=user,
            is_bookmarked=True
        ).select_related("resource")


class CheckpointService:
    """Service for knowledge checkpoint operations."""
    
    @staticmethod
    @transaction.atomic
    def submit_answers(
        user,
        checkpoint: KnowledgeCheckpoint,
        answers: Dict,
        enrollment: Optional[UserLearningPathEnrollment] = None,
    ) -> UserCheckpointAttempt:
        """
        Submit answers for a checkpoint.

        Gate: all resources in the phase must be completed before the user can
        take this checkpoint (server-side enforcement).
        """
        # ── Gate: resources must be completed first ───────────────────────────
        if checkpoint.phase:
            total_resources = checkpoint.phase.resources.count()
            if total_resources > 0:
                completed_resources = UserResourceProgress.objects.filter(
                    user=user,
                    resource__phase=checkpoint.phase,
                    status=UserResourceProgress.ProgressStatus.COMPLETED,
                ).count()
                if completed_resources < total_resources:
                    raise ValueError(
                        f"You must complete all {total_resources} resources in "
                        "this phase before taking the checkpoint."
                    )

        # ── Attempt limit check ───────────────────────────────────────────────
        attempts_count = UserCheckpointAttempt.objects.filter(
            user=user, checkpoint=checkpoint
        ).count()

        if attempts_count >= checkpoint.max_attempts:
            raise ValueError(f"Maximum attempts ({checkpoint.max_attempts}) reached")

        # ── Grade answers ─────────────────────────────────────────────────────
        correct = 0
        total = len(checkpoint.questions)
        feedback = {}

        for q in checkpoint.questions:
            q_id = q.get("id")
            user_answer = answers.get(q_id)
            correct_answer = q.get("correct_answer")
            is_correct = user_answer == correct_answer
            if is_correct:
                correct += 1
            feedback[q_id] = {
                "is_correct": is_correct,
                "explanation": q.get("explanation", ""),
                "topic": q.get("topic", q.get("concept", "General")),
            }

        score = int((correct / total) * 100) if total > 0 else 0
        passed = score >= checkpoint.passing_score

        # ── Persist attempt ───────────────────────────────────────────────────
        attempt = UserCheckpointAttempt.objects.create(
            user=user,
            checkpoint=checkpoint,
            enrollment=enrollment,
            attempt_number=attempts_count + 1,
            answers=answers,
            score=score,
            passed=passed,
            started_at=timezone.now(),
            completed_at=timezone.now(),
            feedback=feedback,
        )

        logger.info(f"User {user.id} scored {score} on checkpoint {checkpoint.id}")

        # ── Run adaptive analysis synchronously ────────────────────────────────
        try:
            from apps.learning.adaptive_engine import AdaptiveEngine
            engine = AdaptiveEngine()
            engine.handle_quiz_completion(attempt)
        except Exception as e:
            logger.warning(f"Adaptive analysis failed: {e}")

        # ── Phase completion check ────────────────────────────────────────────
        if passed and enrollment:
            ResourceProgressService._check_phase_completion(
                user, checkpoint.phase, enrollment
            )

        return attempt


class RecommendationService:
    """Service for learning recommendations."""
    
    @staticmethod
    def get_user_recommendations(user, limit: int = 10) -> List[RecommendedResource]:
        """Get user's recommendations."""
        return RecommendedResource.objects.filter(
            user=user,
            is_dismissed=False
        ).select_related("resource").order_by("-relevance_score")[:limit]


class LearningStatsService:
    """Service for learning statistics."""
    
    @staticmethod
    def get_user_stats(user) -> Dict[str, Any]:
        """Get learning statistics for user."""
        enrollments = UserLearningPathEnrollment.objects.filter(user=user)
        
        total = enrollments.count()
        completed = enrollments.filter(
            status=UserLearningPathEnrollment.EnrollmentStatus.COMPLETED
        ).count()
        in_progress = enrollments.filter(
            status=UserLearningPathEnrollment.EnrollmentStatus.IN_PROGRESS
        ).count()
        
        total_time = enrollments.aggregate(
            total=Sum("total_time_spent_minutes")
        )["total"] or 0
        
        resources_completed = UserResourceProgress.objects.filter(
            user=user,
            status=UserResourceProgress.ProgressStatus.COMPLETED
        ).count()
        
        checkpoints = UserCheckpointAttempt.objects.filter(
            user=user,
            passed=True
        )
        checkpoints_passed = checkpoints.values("checkpoint").distinct().count()
        
        avg_score = UserCheckpointAttempt.objects.filter(
            user=user
        ).aggregate(avg=Avg("score"))["avg"] or 0
        
        return {
            "total_enrollments": total,
            "completed": completed,
            "in_progress": in_progress,
            "total_hours": total_time // 60,
            "resources_completed": resources_completed,
            "checkpoints_passed": checkpoints_passed,
            "average_score": round(float(avg_score), 1)
        }


# =============================================================================
# NEW ADAPTIVE LEARNING SERVICES
# =============================================================================

class ProjectSubmissionService:
    """Service for project submissions and AI review."""
    
    @staticmethod
    @transaction.atomic
    def submit_project(
        user,
        title: str,
        description: str,
        project_url: str,
        phase_id: Optional[UUID] = None,
        enrollment_id: Optional[UUID] = None,
        technologies: List[str] = None,
        skills_demonstrated: List[str] = None,
        live_demo_url: str = ""
    ) -> ProjectSubmission:
        """Submit a project for review."""
        from apps.learning.adaptive_engine import get_adaptive_learning_engine

        phase = None
        enrollment = None
        
        if phase_id:
            phase = LearningPhase.objects.get(id=phase_id)
        
        if enrollment_id:
            enrollment = UserLearningPathEnrollment.objects.get(
                id=enrollment_id,
                user=user
            )
        
        submission = ProjectSubmission.objects.create(
            user=user,
            phase=phase,
            enrollment=enrollment,
            title=title,
            description=description,
            project_url=project_url,
            live_demo_url=live_demo_url,
            technologies=technologies or [],
            skills_demonstrated=skills_demonstrated or [],
            status=ProjectSubmission.SubmissionStatus.SUBMITTED
        )
        
        logger.info(f"Project submitted: {submission.id} by user {user.id}")

        try:
            engine = get_adaptive_learning_engine()
            submission = engine.review_project_submission(submission)
        except Exception as e:
            logger.error(f"Failed to auto-review project {submission.id}: {e}", exc_info=True)
            submission.status = ProjectSubmission.SubmissionStatus.REVIEWED
            submission.ai_review = {
                "error": "Automatic AI review failed",
                "manual_review_required": True,
            }
            submission.reviewed_at = timezone.now()
            submission.save(update_fields=["status", "ai_review", "reviewed_at", "updated_at"])

        return submission
    
    @staticmethod
    def get_user_submissions(
        user,
        status: Optional[str] = None
    ) -> List[ProjectSubmission]:
        """Get user's project submissions."""
        from apps.learning.adaptive_engine import get_adaptive_learning_engine

        queryset = ProjectSubmission.objects.filter(user=user)

        pending_items = list(
            queryset.filter(status=ProjectSubmission.SubmissionStatus.SUBMITTED)
        )
        if pending_items:
            engine = get_adaptive_learning_engine()
            for submission in pending_items:
                try:
                    engine.review_project_submission(submission)
                except Exception as e:
                    logger.error(f"Failed to backfill project review {submission.id}: {e}", exc_info=True)
        
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset.order_by("-created_at")
    
    @staticmethod
    def get_submission_detail(
        user,
        submission_id: UUID
    ) -> Optional[ProjectSubmission]:
        """Get detailed submission with review."""
        try:
            return ProjectSubmission.objects.get(
                id=submission_id,
                user=user
            )
        except ProjectSubmission.DoesNotExist:
            return None


class CertificateVerificationService:
    """Service for certificate verification."""
    
    @staticmethod
    @transaction.atomic
    def submit_certificate(
        user,
        course_name: str,
        platform: str,
        certificate_url: str = "",
        certificate_image: str = "",
        completion_date=None,
        certificate_id: str = "",
        skills_covered: List[str] = None,
        resource_id: Optional[UUID] = None,
        enrollment_id: Optional[UUID] = None
    ) -> CertificateVerification:
        """Submit a certificate for verification."""
        from apps.learning.adaptive_engine import get_adaptive_learning_engine

        resource = None
        enrollment = None
        
        if resource_id:
            resource = LearningResource.objects.get(id=resource_id)
        
        if enrollment_id:
            enrollment = UserLearningPathEnrollment.objects.get(
                id=enrollment_id,
                user=user
            )
        
        verification = CertificateVerification.objects.create(
            user=user,
            resource=resource,
            enrollment=enrollment,
            course_name=course_name,
            platform=platform,
            certificate_url=certificate_url,
            certificate_image=certificate_image,
            completion_date=completion_date,
            certificate_id=certificate_id,
            skills_covered=skills_covered or [],
            status=CertificateVerification.VerificationStatus.PENDING
        )
        
        logger.info(f"Certificate submitted: {verification.id} by user {user.id}")

        try:
            engine = get_adaptive_learning_engine()
            verification = engine.verify_certificate(verification)
        except Exception as e:
            logger.error(f"Failed to auto-verify certificate {verification.id}: {e}", exc_info=True)
            verification.status = CertificateVerification.VerificationStatus.MANUAL_REVIEW
            verification.verification_method = CertificateVerification.VerificationMethod.MANUAL
            verification.verification_notes = "Automatic verification failed. Manual review required."
            verification.save(update_fields=["status", "verification_method", "verification_notes", "updated_at"])

        return verification
    
    @staticmethod
    def get_user_certificates(
        user,
        status: Optional[str] = None
    ) -> List[CertificateVerification]:
        """Get user's certificate verifications."""
        from apps.learning.adaptive_engine import get_adaptive_learning_engine

        queryset = CertificateVerification.objects.filter(user=user)

        pending_items = list(
            queryset.filter(status=CertificateVerification.VerificationStatus.PENDING)
        )
        if pending_items:
            engine = get_adaptive_learning_engine()
            for verification in pending_items:
                try:
                    engine.verify_certificate(verification)
                except Exception as e:
                    logger.error(f"Failed to backfill certificate verification {verification.id}: {e}", exc_info=True)
        
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset.order_by("-created_at")


class SkillMasteryService:
    """Service for skill mastery tracking."""
    
    @staticmethod
    def get_user_skill_masteries(user) -> List[UserSkillMastery]:
        """Get all skill masteries for a user."""
        return UserSkillMastery.objects.filter(
            user=user
        ).order_by("-mastery_score")
    
    @staticmethod
    def get_skill_mastery(user, skill_name: str) -> Optional[UserSkillMastery]:
        """Get mastery for a specific skill."""
        try:
            return UserSkillMastery.objects.get(
                user=user,
                skill_name=skill_name
            )
        except UserSkillMastery.DoesNotExist:
            return None
    
    @staticmethod
    def get_skills_by_level(
        user,
        level: str
    ) -> List[UserSkillMastery]:
        """Get skills at a specific mastery level."""
        return UserSkillMastery.objects.filter(
            user=user,
            mastery_level=level
        )
    
    @staticmethod
    def get_decaying_skills(user) -> List[UserSkillMastery]:
        """Get skills that may be decaying due to inactivity."""
        from apps.learning.adaptive_engine import get_adaptive_learning_engine
        engine = get_adaptive_learning_engine()
        return engine.check_skill_decay(user)
    
    @staticmethod
    def get_skill_summary(user) -> Dict[str, Any]:
        """Get summary of user's skill masteries."""
        masteries = UserSkillMastery.objects.filter(user=user)
        
        total_skills = masteries.count()
        avg_mastery = masteries.aggregate(avg=Avg("mastery_score"))["avg"] or 0
        
        by_level = {
            "expert": masteries.filter(mastery_level="expert").count(),
            "proficient": masteries.filter(mastery_level="proficient").count(),
            "intermediate": masteries.filter(mastery_level="intermediate").count(),
            "beginner": masteries.filter(mastery_level="beginner").count(),
            "novice": masteries.filter(mastery_level="novice").count(),
        }
        
        top_skills = list(masteries.order_by("-mastery_score")[:5].values(
            "skill_name", "mastery_score", "mastery_level"
        ))
        
        needs_attention = list(masteries.filter(
            days_since_practice__gt=30,
            mastery_score__gt=20
        ).values("skill_name", "mastery_score", "days_since_practice")[:5])
        
        return {
            "total_skills": total_skills,
            "average_mastery": round(float(avg_mastery), 1),
            "by_level": by_level,
            "top_skills": top_skills,
            "needs_attention": needs_attention
        }


class RefresherQuizService:
    """Service for skill refresher quizzes."""
    
    @staticmethod
    def get_pending_refreshers(user) -> List[SkillRefresherQuiz]:
        """Get pending refresher quizzes for user."""
        return SkillRefresherQuiz.objects.filter(
            user=user,
            status__in=[
                SkillRefresherQuiz.QuizStatus.PENDING,
                SkillRefresherQuiz.QuizStatus.SENT
            ],
            expires_at__gt=timezone.now()
        ).order_by("-created_at")
    
    @staticmethod
    def generate_refreshers_for_user(user) -> List[SkillRefresherQuiz]:
        """Generate refresher quizzes for skills needing attention."""
        from apps.learning.adaptive_engine import get_adaptive_learning_engine
        engine = get_adaptive_learning_engine()
        
        # Check for decaying skills
        decaying_skills = engine.check_skill_decay(user)
        
        refreshers = []
        for mastery in decaying_skills[:3]:  # Max 3 at a time
            # Check if already has pending refresher
            existing = SkillRefresherQuiz.objects.filter(
                user=user,
                skill_mastery=mastery,
                status__in=[
                    SkillRefresherQuiz.QuizStatus.PENDING,
                    SkillRefresherQuiz.QuizStatus.SENT
                ]
            ).exists()
            
            if not existing:
                quiz = engine.generate_refresher_quiz(user, mastery)
                refreshers.append(quiz)
        
        return refreshers
    
    @staticmethod
    @transaction.atomic
    def submit_refresher_answers(
        user,
        quiz_id: UUID,
        answers: Dict[str, str]
    ) -> SkillRefresherQuiz:
        """Submit answers for a refresher quiz."""
        quiz = SkillRefresherQuiz.objects.get(
            id=quiz_id,
            user=user
        )
        
        if quiz.status == SkillRefresherQuiz.QuizStatus.COMPLETED:
            raise ValueError("Quiz already completed")
        
        if quiz.expires_at and timezone.now() > quiz.expires_at:
            quiz.status = SkillRefresherQuiz.QuizStatus.EXPIRED
            quiz.save()
            raise ValueError("Quiz has expired")
        
        from apps.learning.adaptive_engine import get_adaptive_learning_engine
        engine = get_adaptive_learning_engine()
        
        return engine.process_refresher_quiz_result(quiz, answers)


class PhaseInjectionService:
    """Service for managing phase injections (remedial/advanced content)."""
    
    @staticmethod
    def get_pending_injections(
        enrollment: UserLearningPathEnrollment
    ) -> List[PhaseInjection]:
        """Get pending injections for an enrollment."""
        return PhaseInjection.objects.filter(
            enrollment=enrollment,
            is_completed=False
        ).order_by("-priority", "created_at")
    
    @staticmethod
    def get_injection_detail(
        user,
        injection_id: UUID
    ) -> Optional[PhaseInjection]:
        """Get injection detail."""
        try:
            return PhaseInjection.objects.get(
                id=injection_id,
                enrollment__user=user
            )
        except PhaseInjection.DoesNotExist:
            return None
    
    @staticmethod
    @transaction.atomic
    def complete_injection(
        user,
        injection_id: UUID,
        quiz_answers: Optional[Dict] = None
    ) -> PhaseInjection:
        """Mark an injection as completed."""
        injection = PhaseInjection.objects.get(
            id=injection_id,
            enrollment__user=user
        )
        
        completion_score = None
        
        # If has verification quiz, grade it
        if quiz_answers and injection.verification_quiz:
            questions = injection.verification_quiz.get("questions", [])
            correct = 0
            total = len(questions)
            
            for q in questions:
                q_id = q.get("id", "")
                if quiz_answers.get(q_id) == q.get("correct_answer"):
                    correct += 1
            
            completion_score = int((correct / total) * 100) if total > 0 else 100
        
        injection.is_completed = True
        injection.completed_at = timezone.now()
        injection.completion_score = completion_score
        injection.save()
        
        # Update skill mastery for weak concepts addressed
        if injection.weak_concepts:
            for concept in injection.weak_concepts:
                mastery, _ = UserSkillMastery.objects.get_or_create(
                    user=user,
                    skill_name=concept,
                    defaults={"mastery_score": 0}
                )
                # Remedial completion gives moderate boost
                mastery.mastery_score = min(100, mastery.mastery_score + 10)
                mastery.record_verification(
                    verification_type="remedial",
                    score=completion_score or 80,
                    source=injection.title
                )
                mastery.save()
        
        logger.info(f"Injection {injection.id} completed by user {user.id}")
        
        return injection


class AdaptiveLearningStatsService:
    """Extended stats including adaptive learning metrics."""
    
    @staticmethod
    def get_comprehensive_stats(user) -> Dict[str, Any]:
        """Get comprehensive learning stats including adaptive metrics."""
        # Get basic stats
        basic_stats = LearningStatsService.get_user_stats(user)
        
        # Get skill mastery stats
        skill_stats = SkillMasteryService.get_skill_summary(user)
        
        # Get project stats
        projects = ProjectSubmission.objects.filter(user=user)
        project_stats = {
            "total_submitted": projects.count(),
            "approved": projects.filter(
                status=ProjectSubmission.SubmissionStatus.APPROVED
            ).count(),
            "needs_revision": projects.filter(
                status=ProjectSubmission.SubmissionStatus.NEEDS_REVISION
            ).count(),
            "average_score": projects.filter(
                overall_score__isnull=False
            ).aggregate(avg=Avg("overall_score"))["avg"] or 0
        }
        
        # Get certificate stats
        certificates = CertificateVerification.objects.filter(user=user)
        certificate_stats = {
            "total_submitted": certificates.count(),
            "verified": certificates.filter(
                status=CertificateVerification.VerificationStatus.VERIFIED
            ).count(),
            "pending": certificates.filter(
                status=CertificateVerification.VerificationStatus.PENDING
            ).count()
        }
        
        # Get adaptive learning stats
        all_enrollments = UserLearningPathEnrollment.objects.filter(user=user)
        injections = PhaseInjection.objects.filter(
            enrollment__user=user
        )
        adaptive_stats = {
            "remedial_content_received": injections.filter(
                injection_type=PhaseInjection.InjectionType.REMEDIAL
            ).count(),
            "remedial_completed": injections.filter(
                injection_type=PhaseInjection.InjectionType.REMEDIAL,
                is_completed=True
            ).count(),
            "advanced_content_unlocked": injections.filter(
                injection_type=PhaseInjection.InjectionType.ADVANCED
            ).count(),
            "path_updates": LearningPathUpdate.objects.filter(
                enrollment__user=user
            ).count()
        }
        
        # Get refresher quiz stats
        refreshers = SkillRefresherQuiz.objects.filter(user=user)
        refresher_stats = {
            "total_sent": refreshers.filter(
                status__in=[
                    SkillRefresherQuiz.QuizStatus.SENT,
                    SkillRefresherQuiz.QuizStatus.COMPLETED
                ]
            ).count(),
            "completed": refreshers.filter(
                status=SkillRefresherQuiz.QuizStatus.COMPLETED
            ).count(),
            "passed": refreshers.filter(passed=True).count(),
            "pending": refreshers.filter(
                status__in=[
                    SkillRefresherQuiz.QuizStatus.PENDING,
                    SkillRefresherQuiz.QuizStatus.SENT
                ]
            ).count()
        }
        
        return {
            **basic_stats,
            "skills": skill_stats,
            "projects": project_stats,
            "certificates": certificate_stats,
            "adaptive_learning": adaptive_stats,
            "skill_refreshers": refresher_stats
        }
