"""
AI Prompts Service
==================
All AI prompts and specialized AI operations using Gemini Pro.
"""

import logging
from typing import Any, Dict, List, Optional

from services.ai.gemini import get_gemini_service


logger = logging.getLogger(__name__)


class CareerAIPrompts:
    """
    AI prompts for CareerAI features.
    Uses Gemini Pro for all AI operations.
    """
    
    # =========================================================================
    # SYSTEM PROMPTS
    # =========================================================================
    
    CAREER_PREDICTION_SYSTEM = """You are an expert career counselor and job market analyst with deep knowledge of:
- Current job market trends across industries
- Skill requirements for various roles
- Career progression paths
- Salary benchmarks by role and location
- Emerging technologies and their impact on careers

Analyze user profiles and provide data-driven career predictions with actionable insights.
Always respond in valid JSON format. Be specific, practical, and encouraging while remaining realistic."""

    LEARNING_PATH_SYSTEM = """You are an expert curriculum architect who designs comprehensive, industry-grade career learning roadmaps.
Your sole job is to output a single raw JSON object — no markdown fences, no preamble, no trailing text.

Design principles:
  1. Generate 10-14 phases covering EVERYTHING from absolute foundation to production-level expertise.
2. Include adjacent career skills professionals actually need (e.g. Data Scientists need SQL, Git, Cloud, Viz tools).
3. Phases progress logically: foundation → core → intermediate → advanced → expert → career-ready.
4. Every phase has clear, measurable learning objectives ("you will be able to...") and a readiness checklist.
5. Resources are REAL — name actual courses, books, YouTube channels — but provide search_query, NOT hardcoded URL.
6. Each phase difficulty increases gradually. Phase 1 is always beginner-accessible.
  7. Total estimated_hours must realistically match hours_per_week × timeline_weeks (minimum 140h for complete tracks).
  8. Cover the REAL career: what a practitioner does on day 1, day 100, and day 1000 at their job.
  9. Every complete path must include: foundations, core stack, databases/data layer, testing, security, system design, cloud/deployment, observability, and portfolio/interview preparation.

Output rules — violating any of these will break the parser:
- Return ONLY the raw JSON object. Zero text before or after.
- No markdown fences (no ```json).
- No comments inside JSON.
- All keys must be double-quoted strings.
- No trailing commas.
  - Minimum 10 phases. If in doubt, generate more phases."""

    RESUME_ANALYSIS_SYSTEM = """You are an expert ATS (Applicant Tracking System) analyst and resume reviewer with experience in:
1. ATS optimization and keyword matching
2. Resume formatting best practices
3. Industry-specific requirements
4. Quantifying achievements

Analyze resumes objectively. Provide actionable feedback. Respond in valid JSON format."""

    INTERVIEW_SYSTEM = """You are an expert technical interviewer with experience at top tech companies. Create realistic, challenging interview questions that:
1. Test theoretical knowledge and practical application
2. Match the specified difficulty level
3. Cover a range of topics
4. Have clear evaluation criteria

For behavioral questions, use STAR format. For technical, include expected key points.
Respond in valid JSON format."""

    ANSWER_EVALUATION_SYSTEM = """You are an expert interview evaluator providing constructive feedback. You:
1. Evaluate fairly and thoroughly
2. Recognize strengths and improvements
3. Provide specific, actionable feedback
4. Score consistently

Be encouraging but honest. Focus on helping the candidate improve.
Respond in valid JSON format."""

    CHATBOT_SYSTEM = """You are CareerPilot, a friendly career guidance assistant helping with:
- Career planning and transitions
- Resume and cover letter advice
- Interview preparation
- Skill development
- Job search strategies

PERSONALITY:
- Friendly, professional, encouraging
- Provide specific, actionable advice
- Ask clarifying questions when needed
- Keep responses concise (2-4 paragraphs max)
- Use bullet points for lists

You have access to user's profile, resume, and learning progress. Use this context to personalize responses."""

    # =========================================================================
    # CAREER PREDICTION
    # =========================================================================
    
    @staticmethod
    def generate_career_predictions(
        current_role: str,
        experience_years: float,
        education_level: str,
        education_field: str,
        skills: List[str],
        target_industries: List[str],
        target_roles: List[str],
        career_level: str,
        location: str,
        salary_expectation: Optional[float] = None,
        timeline_years: int = 5
    ) -> Dict[str, Any]:
        """Generate career predictions using Gemini."""
        
        prompt = f"""Analyze the following user profile and provide career predictions:

## USER PROFILE
- **Current Role**: {current_role or 'Not specified'}
- **Years of Experience**: {experience_years}
- **Education**: {education_level} in {education_field}
- **Current Skills**: {', '.join(skills) if skills else 'Not specified'}
- **Target Industries**: {', '.join(target_industries) if target_industries else 'Open to all'}
- **Target Roles**: {', '.join(target_roles) if target_roles else 'Open to suggestions'}
- **Career Level Goal**: {career_level or 'Next level'}
- **Preferred Location**: {location or 'Flexible'}
- **Salary Expectation**: {'$' + str(salary_expectation) if salary_expectation else 'Market rate'}
- **Timeline**: {timeline_years} years

Provide 3-5 career predictions. For each prediction include:
1. predicted_career: Job title
2. match_score: 0-100 based on skill alignment
3. reasoning: 2-3 sentences explaining the match
4. skills_matched: Array of applicable user skills
5. skills_to_develop: Array of skills to learn (max 5)
6. market_demand: Current demand with job opening estimates
7. salary_range: Realistic salary range object with min/max
8. growth_potential: Career growth outlook
9. trends: Object with current, future, and technologies

## RESPONSE FORMAT (JSON)
{{
  "predictions": [
    {{
      "predicted_career": "string",
      "match_score": number,
      "reasoning": "string",
      "skills_matched": ["array"],
      "skills_to_develop": ["array"],
      "market_demand": "string",
      "salary_range": {{"min": number, "max": number, "currency": "USD"}},
      "growth_potential": "string",
      "trends": {{
        "current": "string",
        "future": "string",
        "technologies": ["array"]
      }}
    }}
  ],
  "summary": "Brief overall career outlook",
  "confidence_score": number
}}"""

        gemini = get_gemini_service()
        return gemini.generate_json(
            prompt=prompt,
            system_prompt=CareerAIPrompts.CAREER_PREDICTION_SYSTEM,
            temperature=0.7,
            max_tokens=3000
        )
    
    # =========================================================================
    # LEARNING PATH GENERATION
    # =========================================================================
    
    @staticmethod
    def generate_learning_path(
        career_goal: str,
        target_role: str,
        current_skills: List[str],
        skills_to_learn: List[str],
        experience_level: str,
        hours_per_week: int,
        # Extended personalisation parameters
        user_context: Optional[Dict[str, Any]] = None,
        expert_skills: Optional[List[str]] = None,
        completed_paths: Optional[List[str]] = None,
        learning_style: str = "mixed",
        timeline_weeks: int = 12,
    ) -> Dict[str, Any]:
        """
        Generate a complete end-to-end career learning path with 10-14 comprehensive phases
        covering everything from basics to advanced — including adjacent/cross-domain skills
        that real-world practitioners in the role actually use.
        Resources use search_query instead of URL so links never go stale.
        """
        ctx = user_context or {}
        experience_years = ctx.get("experience_years", 0)
        current_role = ctx.get("current_role", "")
        education = ctx.get("education", "")
        skill_proficiency = ctx.get("skill_proficiency", {})
        career_goals_list = ctx.get("career_goals", [])

        proficiency_lines = "\n".join(
            f"  - {skill}: {level}"
            for skill, level in list(skill_proficiency.items())[:15]
        )
        expert_block = (
            "SKIP skills already mastered: " + ", ".join(expert_skills)
            if expert_skills
            else ""
        )
        completed_block = (
            "DO NOT repeat content from completed paths:\n"
            + "\n".join(f"  - {t}" for t in completed_paths)
            if completed_paths
            else ""
        )
        total_hours = max(hours_per_week * timeline_weeks, 120)

        prompt = f"""You are a senior curriculum architect. Generate a COMPLETE, COMPREHENSIVE learning path as a raw JSON object.

## USER PROFILE
- Target role: {target_role}
- Career goal: {career_goal}
- Current role: {current_role or 'student/learner'}
- Experience: {experience_years} year(s) | Level: {experience_level}
- Education: {education or 'not specified'}
- Available: {hours_per_week} h/week for {timeline_weeks} weeks (~{total_hours} h total)
- Learning style: {learning_style}

## CURRENT SKILLS (skip these unless building on them)
{', '.join(current_skills) if current_skills else 'None — complete beginner'}

## PROFICIENCY LEVELS
{proficiency_lines or 'Not provided'}

## REQUIRED SKILLS TO COVER
{', '.join(skills_to_learn) if skills_to_learn else 'Derive all required skills from target role'}

{expert_block}
{completed_block}

## CRITICAL INSTRUCTION — PHASE COVERAGE
Design 10-14 phases that give a COMPLETE CAREER CURRICULUM from scratch to industry-ready.
Think like a senior engineer mentoring a junior: what does someone ACTUALLY need day-to-day?

For a Data Science / ML role, phases should cover:
  Foundation Math & Stats → Python Programming → Data Wrangling & SQL →
  Data Visualization → Machine Learning → Deep Learning & Neural Networks →
  NLP & LLMs → MLOps & Deployment → Cloud Platforms (AWS/GCP/Azure) →
  Data Engineering Foundations → Advanced AI & Research → Portfolio & Career

For a Full Stack Developer role, phases should cover:
  Web Fundamentals → Frontend (HTML/CSS/JS/React) → Backend (Node/Python/Django) →
  Databases & SQL → APIs & REST → DevOps & CI/CD → Cloud & Deployment →
  System Design → Security → Testing → Advanced Patterns → Portfolio & Career

For ANY role: start from absolute fundamentals, cover all adjacent skills professionals use,
end with production-level advanced topics AND career/portfolio readiness.

## MANDATORY COVERAGE FOR EVERY CAREER PATH
Regardless of role, include phases that cover all of these dimensions across the full path:
- Prerequisites and foundations
- Core role-specific stack and workflows
- Data layer / persistence / data modeling
- APIs and integration patterns
- Testing and quality engineering
- Security fundamentals and secure-by-default practices
- System design and scalability
- Cloud, deployment, and DevOps/CI-CD
- Monitoring, logging, and reliability
- Portfolio, interview prep, and career launch assets

## ADJACENT SKILLS MANDATE
Include phases/skills that are NOT the core skill but are REQUIRED to be effective in the role.
Examples: Data Scientists need SQL, visualization tools, Git, cloud deployment, communication.
Full Stack devs need Docker, Linux basics, DB design, caching, monitoring.

## OUTPUT FORMAT (exact raw JSON — zero text outside braces)
{{
  "title": "<inspiring 8-12 word title>",
  "description": "<3 sentences: what learner achieves, why this path is complete, career outcome>",
  "difficulty": "beginner|intermediate|advanced",
  "estimated_weeks": {timeline_weeks},
  "total_hours": {total_hours},
  "skills_covered": ["skill1", "skill2", "...all major skills"],
  "career_outcome": "<one powerful sentence: what job/role this path unlocks>",
  "difficulty_progression": "beginner → intermediate → advanced → expert",
  "phases": [
    {{
      "title": "Phase N: <clear topic name>",
      "description": "<2-3 sentences: what this phase covers and why it matters for {target_role}>",
      "order": 1,
      "difficulty": "beginner|intermediate|advanced|expert",
      "phase_outcome": "<one sentence: what career door this phase opens>",
      "skills_covered": ["skill1", "skill2", "skill3"],
      "topics_covered": ["Topic 1", "Topic 2", "Topic 3", "Topic 4", "Topic 5"],
      "estimated_hours": 20,
      "learning_objectives": [
        "Verb + specific outcome 1 (e.g. 'Build statistical models using NumPy and SciPy')",
        "Verb + specific outcome 2",
        "Verb + specific outcome 3"
      ],
      "prerequisite_skills": ["skill needed before this phase — empty list for phase 1"],
      "readiness_checklist": [
        "Can you explain <core concept> without looking it up?",
        "Have you completed at least one project using <skill>?",
        "Can you debug <common problem> independently?"
      ],
      "resources": [
        {{
          "title": "<real course/book/channel name>",
          "type": "course|video|article|tutorial|documentation|book|project",
          "provider": "YouTube|Udemy|Coursera|freeCodeCamp|GitHub|Docs|Medium|Pluralsight|edX|MIT OpenCourseWare|fast.ai|Kaggle|DataCamp|O'Reilly",
          "search_query": "<precise search string to find this resource on that provider>",
          "is_free": true,
          "description": "<one sentence: what makes this resource ideal for this phase>"
        }}
      ],
      "youtube_queries": [
        "<specific YouTube search e.g. 'pandas dataframe tutorial 2024 complete'>",
        "<another specific query>",
        "<third query covering a different sub-topic>"
      ],
      "external_topics": [
        {{"site": "GeeksForGeeks", "topic": "<exact topic>"}},
        {{"site": "TutorialsPoint", "topic": "<exact topic>"}},
        {{"site": "freeCodeCamp", "topic": "<exact topic>"}},
        {{"site": "Kaggle", "topic": "<exact topic — for DS/ML phases>"}},
        {{"site": "dev.to", "topic": "<exact topic>"}}
      ],
      "recommended_certifications": [
        {{
          "name": "<real certification name>",
          "platform": "Coursera|Udemy|Google|AWS|Microsoft|LinkedIn|Kaggle|DataCamp",
          "search_query": "<search to find this cert>",
          "is_free": false,
          "relevance": "<one sentence: why this cert matters for {target_role}>"
        }}
      ],
      "capstone_project": {{
        "title": "<project name>",
        "description": "<2-3 sentences: exactly what to build, what dataset/API to use, what it proves>",
        "deliverables": ["working code on GitHub", "README with results", "deployed demo or report"],
        "skills_demonstrated": ["skill1", "skill2"],
        "estimated_hours": 10,
        "github_search_query": "<GitHub search to find similar reference projects>",
        "difficulty_level": "beginner|intermediate|advanced"
      }}
    }}
  ]
}}

STRICT RULES:
1. Generate 10-14 phases — DO NOT generate fewer than 10.
2. Cover the COMPLETE journey: absolute basics → production-level advanced topics.
3. Include adjacent career skills (e.g. Git, Linux, Cloud, Communication, Portfolio).
4. 4-6 resources per phase (mix: 1 video course + 1 book/article + 1 official docs + 1 hands-on + 1 project/exercise).
5. All estimated_hours must sum to approximately {total_hours}.
6. learning_objectives: exactly 3 items, action-verb first, specific and measurable.
7. readiness_checklist: exactly 3 items, phrased as self-assessment questions.
8. topics_covered: 4-8 specific topics, ordered from basic to advanced within the phase.
9. NEVER include a "url" field. Only "search_query".
10. Raw JSON ONLY — zero markdown, zero text outside the JSON object."""

        gemini = get_gemini_service()
        return gemini.generate_json(
            prompt=prompt,
            system_prompt=CareerAIPrompts.LEARNING_PATH_SYSTEM,
            temperature=0.4,
            max_tokens=8000,
        )

    @staticmethod
    def generate_phase_deep_dive(
        phase_title: str,
        phase_description: str,
        career_goal: str,
        skills_covered: List[str],
        topics_covered: List[str],
        difficulty: str,
        phase_order: int,
        total_phases: int,
        current_skills: List[str],
    ) -> Dict[str, Any]:
        """
        Generate a deep, detailed curriculum for a single phase.
        Called lazily when a user first clicks into a phase.
        Returns rich content: ordered topics with sub-topics, multiple resource types,
        3 projects (beginner→advanced), certifications, interview Q&A, readiness checklist.
        """
        prompt = f"""You are a senior educator and industry expert. Generate deeply detailed curriculum content for ONE learning phase as a raw JSON object.

## PHASE CONTEXT
- Phase {phase_order} of {total_phases}: {phase_title}
- Career Goal: {career_goal}
- Description: {phase_description}
- Difficulty: {difficulty}
- Core Skills: {', '.join(skills_covered) if skills_covered else 'See phase title'}
- Topics to Cover: {', '.join(topics_covered) if topics_covered else 'Derive from phase title and skills'}
- Learner's existing skills: {', '.join(current_skills[:15]) if current_skills else 'beginner'}

## YOUR TASK
Produce a complete, practical deep-dive curriculum for this phase that a real working engineer would endorse.
Think: "what would a senior mentor at Google/Meta teach a junior in this phase?"

## OUTPUT FORMAT (raw JSON only — no markdown, no text outside braces)
{{
  "overview": "<3-4 sentences: what this phase covers, why it is critical for the career, what the learner will be capable of>",
  "topics": [
    {{
      "title": "<Topic Name>",
      "description": "<2 sentences explaining this topic and its importance>",
      "subtopics": ["subtopic 1", "subtopic 2", "subtopic 3", "subtopic 4"],
      "estimated_hours": 4,
      "difficulty": "beginner|intermediate|advanced",
      "why_important": "<one sentence: real-world relevance>"
    }}
  ],
  "video_courses": [
    {{
      "title": "<Real course name on YouTube or platform>",
      "provider": "YouTube|Coursera|Udemy|freeCodeCamp|MIT OCW|fast.ai|DataCamp|Kaggle",
      "search_query": "<precise search to find this on the platform>",
      "is_free": true,
      "estimated_hours": 8,
      "level": "beginner|intermediate|advanced",
      "why_best": "<one sentence: why this video course is the best for this topic>"
    }}
  ],
  "articles_and_docs": [
    {{
      "title": "<Article/documentation title>",
      "provider": "Medium|GeeksForGeeks|freeCodeCamp|Official Docs|Towards Data Science|dev.to|Kaggle Notebooks",
      "search_query": "<search to find this>",
      "is_free": true,
      "type": "article|documentation|notebook|guide",
      "why_read": "<one sentence: what insight this adds>"
    }}
  ],
  "books": [
    {{
      "title": "<Real book title>",
      "author": "<Author name>",
      "search_query": "<title + author search>",
      "is_free": false,
      "chapters_relevant": ["Chapter N: <name>", "Chapter M: <name>"],
      "why_read": "<one sentence: why this book for this phase>"
    }}
  ],
  "projects": [
    {{
      "title": "<Project name>",
      "difficulty": "beginner|intermediate|advanced",
      "description": "<3-4 sentences: exactly what to build, what data/API to use, what challenges it solves>",
      "deliverables": ["GitHub repo with clean code", "README with methodology", "item3"],
      "skills_demonstrated": ["skill1", "skill2", "skill3"],
      "estimated_hours": 12,
      "dataset_or_api": "<real dataset name, Kaggle dataset, public API, or 'generate synthetic data'>",
      "github_search_query": "<GitHub search for reference implementations>",
      "real_world_relevance": "<one sentence: where similar work is done in industry>"
    }}
  ],
  "certifications": [
    {{
      "name": "<Real certification name>",
      "platform": "Coursera|Google|AWS|Microsoft|LinkedIn|Kaggle|DataCamp|Udemy",
      "search_query": "<search to find this cert>",
      "is_free": false,
      "estimated_cost_usd": 50,
      "time_to_complete_weeks": 4,
      "industry_value": "<one sentence: how valued is this cert by employers>",
      "prerequisite": "<what to know before attempting this cert>"
    }}
  ],
  "interview_questions": [
    {{
      "question": "<Real technical interview question for this phase's topics>",
      "answer": "<Detailed answer with code example if applicable — 3-6 sentences>",
      "difficulty": "easy|medium|hard",
      "category": "conceptual|coding|system-design|behavioral",
      "follow_up": "<likely follow-up question an interviewer would ask>"
    }}
  ],
  "readiness_checklist": [
    "<Self-assessment question 1: Can you X without looking it up?>",
    "<Self-assessment question 2: Have you built Y from scratch?>",
    "<Self-assessment question 3: Can you explain Z to a non-technical person?>",
    "<Self-assessment question 4>",
    "<Self-assessment question 5>"
  ],
  "common_mistakes": [
    "<Mistake beginners make in this phase and how to avoid it>",
    "<Mistake 2>",
    "<Mistake 3>"
  ],
  "real_world_applications": [
    "<How this phase's skills are used at companies like Google/Netflix/Uber>",
    "<Application 2>",
    "<Application 3>"
  ],
  "next_phase_preview": "<One sentence: what the next phase builds on from this one>"
}}

STRICT RULES:
1. topics: 5-8 ordered topics, each with 3-5 subtopics — ordered from basic to advanced.
2. video_courses: 4-6 entries (1 beginner + 2 intermediate + 1-2 advanced + 1 project-focused).
3. articles_and_docs: 4-6 entries covering different sub-topics.
4. books: 2-3 entries (only well-known real books — e.g. 'Hands-On Machine Learning' by Aurélien Géron).
5. projects: exactly 3 entries (one beginner, one intermediate, one advanced/production-level).
6. certifications: 2-4 entries, at least one free option if it exists.
7. interview_questions: 8-12 questions across easy/medium/hard and different categories.
8. readiness_checklist: exactly 5 self-assessment questions.
9. All content must be specific and real — no generic placeholder text.
10. Raw JSON ONLY — zero markdown, zero text outside the JSON object."""

        gemini = get_gemini_service()
        return gemini.generate_json(
            prompt=prompt,
            system_prompt=CareerAIPrompts.LEARNING_PATH_SYSTEM,
            temperature=0.4,
            max_tokens=6000,
        )
    
    # =========================================================================
    # RESUME ANALYSIS
    # =========================================================================
    
    @staticmethod
    def analyze_resume(
        resume_text: str,
        job_description: Optional[str] = None,
        target_role: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analyze resume using Gemini."""
        
        job_context = ""
        if job_description:
            job_context = f"\n## TARGET JOB DESCRIPTION\n{job_description[:2000]}"
        elif target_role:
            job_context = f"\n## TARGET ROLE\n{target_role}"
        
        prompt = f"""Analyze this resume for ATS compatibility and quality:

## RESUME CONTENT
{resume_text[:4000]}
{job_context}

Provide comprehensive analysis:
1. ATS Score (0-100)
2. Section-by-section analysis with scores
3. Keywords found vs missing for the target role
4. Specific improvement suggestions with priority
5. Strengths and weaknesses

## RESPONSE FORMAT (JSON)
{{
  "ats_score": number,
  "overall_score": number,
  "sections": {{
    "summary": {{"score": number, "feedback": "string", "suggestions": ["array"]}},
    "experience": {{"score": number, "feedback": "string", "suggestions": ["array"]}},
    "skills": {{"score": number, "feedback": "string", "suggestions": ["array"]}},
    "education": {{"score": number, "feedback": "string", "suggestions": ["array"]}},
    "formatting": {{"score": number, "feedback": "string", "suggestions": ["array"]}}
  }},
  "keywords": {{
    "found": ["array of keywords found"],
    "missing": ["array of important missing keywords"]
  }},
  "improvements": [
    {{"priority": "high|medium|low", "category": "content|formatting|keywords", "suggestion": "string"}}
  ],
  "strengths": ["array of strengths"],
  "weaknesses": ["array of weaknesses"],
  "extracted_skills": ["array of skills found in resume"]
}}"""

        gemini = get_gemini_service()
        return gemini.generate_json(
            prompt=prompt,
            system_prompt=CareerAIPrompts.RESUME_ANALYSIS_SYSTEM,
            temperature=0.3,
            max_tokens=2500
        )
    
    # =========================================================================
    # INTERVIEW QUESTIONS
    # =========================================================================
    
    @staticmethod
    def generate_interview_questions(
        role: str,
        interview_type: str,
        topics: List[str],
        difficulty: str,
        num_questions: int = 5
    ) -> Dict[str, Any]:
        """Generate interview questions using Gemini."""
        
        prompt = f"""Generate interview questions:

## PARAMETERS
- **Role**: {role}
- **Interview Type**: {interview_type}
- **Topics to Cover**: {', '.join(topics) if topics else 'General for the role'}
- **Difficulty**: {difficulty}
- **Number of Questions**: {num_questions}

For each question, provide:
1. The question text
2. Category (technical, behavioral, situational)
3. Difficulty level
4. Expected key points in the answer
5. Potential follow-up questions
6. Suggested time limit

## RESPONSE FORMAT (JSON)
{{
  "questions": [
    {{
      "question": "Question text",
      "category": "technical|behavioral|situational",
      "difficulty": "easy|medium|hard",
      "topic": "Specific topic",
      "expected_points": ["Key points expected in answer"],
      "follow_ups": ["Potential follow-up questions"],
      "time_limit_seconds": 300,
      "tips": "Brief tip for answering"
    }}
  ],
  "interview_tips": ["General tips for this type of interview"]
}}"""

        gemini = get_gemini_service()
        return gemini.generate_json(
            prompt=prompt,
            system_prompt=CareerAIPrompts.INTERVIEW_SYSTEM,
            temperature=0.6,
            max_tokens=2000
        )
    
    # =========================================================================
    # ANSWER EVALUATION
    # =========================================================================
    
    @staticmethod
    def evaluate_interview_answer(
        question: str,
        answer: str,
        expected_points: List[str],
        difficulty: str,
        role: str,
        time_taken_seconds: int,
        time_limit_seconds: int = 300
    ) -> Dict[str, Any]:
        """Evaluate interview answer using Gemini."""
        
        prompt = f"""Evaluate this interview answer:

## QUESTION
{question}

## EXPECTED KEY POINTS
{', '.join(expected_points) if expected_points else 'General competency'}

## CANDIDATE'S ANSWER
{answer[:2000]}

## CONTEXT
- Role: {role}
- Difficulty: {difficulty}
- Time Taken: {time_taken_seconds} seconds
- Time Allowed: {time_limit_seconds} seconds

Evaluate the answer fairly and provide constructive feedback.

## RESPONSE FORMAT (JSON)
{{
  "overall_score": number,
  "scores": {{
    "content": number,
    "structure": number,
    "clarity": number,
    "relevance": number
  }},
  "feedback": {{
    "summary": "1-2 sentence assessment",
    "strengths": ["What was done well"],
    "improvements": ["Specific areas to improve"],
    "missing_points": ["Important points not covered"]
  }},
  "suggestions": ["Actionable suggestions for improvement"],
  "example_response": "Brief example of how to improve the weakest aspect"
}}"""

        gemini = get_gemini_service()
        return gemini.generate_json(
            prompt=prompt,
            system_prompt=CareerAIPrompts.ANSWER_EVALUATION_SYSTEM,
            temperature=0.3,
            max_tokens=1500
        )
    
    # =========================================================================
    # CHATBOT
    # =========================================================================
    
    @staticmethod
    def chat_response(
        message: str,
        conversation_history: List[Dict[str, str]] = None,
        user_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate chatbot response using Gemini with suggestions and actions."""
        
        # Build context from user profile
        context_str = ""
        if user_context:
            context_str = "\n## USER CONTEXT\n"
            if user_context.get("user_name"):
                context_str += f"- Name: {user_context['user_name']}\n"
            if user_context.get("current_role"):
                context_str += f"- Current Role: {user_context['current_role']}\n"
            if user_context.get("skills"):
                context_str += f"- Skills: {', '.join(user_context['skills'][:10])}\n"
            if user_context.get("career_level"):
                context_str += f"- Career Level: {user_context['career_level']}\n"
            if user_context.get("years_experience"):
                context_str += f"- Experience: {user_context['years_experience']} years\n"
        
        # Build conversation context
        history_str = ""
        if conversation_history:
            for msg in conversation_history[-6:]:  # Last 3 exchanges
                role = msg.get("role", "user")
                content = msg.get("content", "")[:300]
                history_str += f"\n{role.upper()}: {content}"
        
        prompt = f"""You are CareerPilot, a helpful career guidance assistant.

{context_str}

{f"CONVERSATION HISTORY:{history_str}" if history_str else ""}

USER MESSAGE: {message}

Respond helpfully and provide relevant follow-up suggestions.

## RESPONSE FORMAT (JSON)
{{
  "response": "Your helpful response here (2-4 paragraphs max)",
  "suggestions": [
    "Follow-up question 1",
    "Follow-up question 2", 
    "Follow-up question 3"
  ],
  "actions": [
    {{
      "type": "navigate",
      "label": "Action label",
      "url": "/path/to/page"
    }}
  ],
  "related_topics": ["topic1", "topic2"]
}}"""

        system_prompt = CareerAIPrompts.CHATBOT_SYSTEM
        
        gemini = get_gemini_service()
        result = gemini.generate_json(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.7,
            max_tokens=1000
        )
        
        # Ensure we return a proper dict even if generation fails
        if not result or "error" in result:
            return {
                "response": "I'm here to help with your career questions! What would you like to know about?",
                "suggestions": [
                    "What career paths match my skills?",
                    "How can I improve my resume?",
                    "Help me prepare for interviews"
                ],
                "actions": [],
                "related_topics": []
            }
        
        return result
    
    # =========================================================================
    # COVER LETTER GENERATION
    # =========================================================================
    
    @staticmethod
    def generate_cover_letter(
        resume_summary: str,
        job_title: str,
        company_name: str,
        job_description: str,
        user_name: str
    ) -> Dict[str, Any]:
        """Generate cover letter using Gemini."""
        
        prompt = f"""Generate a professional cover letter:

## USER PROFILE
{resume_summary[:1500]}

## JOB DETAILS
- Position: {job_title}
- Company: {company_name}
- Description: {job_description[:1000]}

## USER NAME
{user_name}

Create a compelling, personalized cover letter that:
1. Shows enthusiasm for the specific role and company
2. Highlights relevant experience and skills
3. Demonstrates knowledge of the company
4. Uses professional but engaging tone
5. Is concise (3-4 paragraphs)

## RESPONSE FORMAT (JSON)
{{
  "cover_letter": "Full cover letter text",
  "key_points": ["Main selling points highlighted"],
  "customization_tips": ["How to further personalize"]
}}"""

        gemini = get_gemini_service()
        return gemini.generate_json(
            prompt=prompt,
            system_prompt="You are an expert cover letter writer who creates compelling, personalized letters that get interviews. Respond in JSON format.",
            temperature=0.7,
            max_tokens=1500
        )
    
    # =========================================================================
    # SKILL GAP ANALYSIS
    # =========================================================================
    
    @staticmethod
    def analyze_skill_gaps(
        current_skills: List[str],
        target_role: str,
        target_industry: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analyze skill gaps for target role using Gemini."""
        
        prompt = f"""Analyze skill gaps for career transition:

## CURRENT SKILLS
{', '.join(current_skills) if current_skills else 'Not specified'}

## TARGET
- Role: {target_role}
- Industry: {target_industry or 'General'}

Identify:
1. Skills the user already has that are valuable
2. Critical skills missing for the target role
3. Nice-to-have skills that would help
4. Learning priority order
5. Estimated time to develop each skill

## RESPONSE FORMAT (JSON)
{{
  "matching_skills": [
    {{"skill": "string", "relevance": "high|medium|low", "notes": "string"}}
  ],
  "critical_gaps": [
    {{"skill": "string", "importance": "critical", "learning_time": "X weeks", "resources": ["suggested resources"]}}
  ],
  "recommended_skills": [
    {{"skill": "string", "importance": "recommended", "learning_time": "X weeks"}}
  ],
  "learning_roadmap": [
    {{"phase": 1, "skills": ["array"], "duration": "X weeks"}}
  ],
  "readiness_score": number,
  "summary": "Overall assessment"
}}"""

        gemini = get_gemini_service()
        return gemini.generate_json(
            prompt=prompt,
            system_prompt="You are a career skills analyst who helps professionals identify and bridge skill gaps. Respond in JSON format.",
            temperature=0.5,
            max_tokens=2000
        )


# Export for easy import
def get_career_ai_prompts() -> CareerAIPrompts:
    """Get CareerAIPrompts instance."""
    return CareerAIPrompts()


# Alias for backwards compatibility
AIPromptsService = CareerAIPrompts
