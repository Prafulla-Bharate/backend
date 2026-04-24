"""
Interview Question Bank & Evaluation System
=============================================
Pre-built question bank with evaluation rubrics.
Eliminates LLM dependency for core interview functionality.

Real-world systems like Pramp, InterviewBit use:
1. Large question bank (500+ curated questions)
2. Rubric-based evaluation (keywords, structure, STAR method)
3. Pre-defined follow-up questions
4. No LLM at runtime - pure algorithmic evaluation

Usage:
    bank = InterviewQuestionBank()
    questions = bank.get_questions("behavioral", "medium", 5)
    
    evaluator = ResponseEvaluator()
    score = evaluator.evaluate_response(question, response)
"""

import json
import logging
import random
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum

logger = logging.getLogger(__name__)


class QuestionType(Enum):
    BEHAVIORAL = "behavioral"
    TECHNICAL = "technical"
    SITUATIONAL = "situational"
    SYSTEM_DESIGN = "system_design"
    CODING = "coding"
    HR = "hr"


class DifficultyLevel(Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


@dataclass
class EvaluationRubric:
    """Rubric for evaluating interview responses."""
    required_keywords: List[str] = field(default_factory=list)
    bonus_keywords: List[str] = field(default_factory=list)
    min_word_count: int = 50
    max_word_count: int = 500
    structure_elements: List[str] = field(default_factory=list)  # ["situation", "task", "action", "result"]
    technical_concepts: List[str] = field(default_factory=list)
    points_breakdown: Dict[str, int] = field(default_factory=dict)


@dataclass
class InterviewQuestionData:
    """Complete interview question with metadata."""
    id: int
    question: str
    question_type: str
    difficulty: str
    category: str
    tags: List[str]
    companies: List[str]  # Known to be asked at
    expected_topics: List[str]
    sample_answer: str
    answer_tips: List[str]
    follow_ups: List[str]
    rubric: EvaluationRubric
    # STAR hints for behavioral
    situation_hint: str = ""
    task_hint: str = ""
    action_hint: str = ""
    result_hint: str = ""


# =============================================================================
# COMPREHENSIVE INTERVIEW QUESTION BANK - INDIA FOCUSED
# =============================================================================

BEHAVIORAL_QUESTIONS = [
    {
        "question": "Tell me about a time when you had to work under pressure to meet a deadline.",
        "category": "Time Management",
        "tags": ["pressure", "deadline", "time management", "stress"],
        "companies": ["TCS", "Infosys", "Wipro", "Google", "Amazon"],
        "expected_topics": ["deadline", "prioritization", "outcome", "learning"],
        "sample_answer": "In my previous role at XYZ, we had a critical project with a tight 2-week deadline. I prioritized tasks, delegated effectively, and worked extra hours. We delivered on time with 98% quality score.",
        "answer_tips": [
            "Use STAR method (Situation, Task, Action, Result)",
            "Quantify the outcome if possible",
            "Show what you learned from the experience",
            "Be specific about your actions, not the team's"
        ],
        "follow_ups": [
            "What would you do differently next time?",
            "How did you prioritize the tasks?",
            "What was the most challenging part?"
        ],
        "rubric": {
            "required_keywords": ["deadline", "pressure", "delivered", "result"],
            "bonus_keywords": ["prioritized", "organized", "learned", "improved"],
            "structure_elements": ["situation", "task", "action", "result"],
            "min_word_count": 100,
            "points_breakdown": {"structure": 30, "content": 40, "specificity": 30}
        },
        "situation_hint": "Describe the project and the pressure situation",
        "task_hint": "What was expected of you specifically?",
        "action_hint": "What specific steps did you take?",
        "result_hint": "What was the outcome? Use numbers if possible",
        "difficulty": "medium"
    },
    {
        "question": "Describe a situation where you had a conflict with a team member. How did you resolve it?",
        "category": "Conflict Resolution",
        "tags": ["conflict", "teamwork", "communication", "interpersonal"],
        "companies": ["Microsoft", "Google", "Amazon", "Flipkart", "Paytm"],
        "expected_topics": ["conflict", "communication", "resolution", "relationship"],
        "sample_answer": "I once disagreed with a colleague about the technical approach. I scheduled a private meeting, listened to their perspective, found common ground, and we agreed on a hybrid solution that worked better.",
        "answer_tips": [
            "Don't blame the other person",
            "Focus on the resolution, not the conflict",
            "Show empathy and listening skills",
            "Highlight positive outcome for the team"
        ],
        "follow_ups": [
            "What did you learn about yourself?",
            "How is your relationship with that person now?",
            "Would you handle it differently today?"
        ],
        "rubric": {
            "required_keywords": ["conflict", "resolved", "communication", "team"],
            "bonus_keywords": ["listened", "understood", "compromise", "improved"],
            "structure_elements": ["situation", "task", "action", "result"],
            "min_word_count": 100,
            "points_breakdown": {"structure": 25, "content": 40, "emotional_intelligence": 35}
        },
        "situation_hint": "Describe the conflict without blaming",
        "task_hint": "What needed to be resolved?",
        "action_hint": "How did you approach the conversation?",
        "result_hint": "What was the outcome for the team?",
        "difficulty": "medium"
    },
    {
        "question": "Tell me about a time you failed. What did you learn?",
        "category": "Self-Awareness",
        "tags": ["failure", "learning", "growth", "resilience"],
        "companies": ["Google", "Amazon", "Microsoft", "Uber", "Ola"],
        "expected_topics": ["failure", "mistake", "learning", "improvement"],
        "sample_answer": "I once underestimated a project's complexity and missed a deadline. I learned to always add buffer time and break down tasks better. Now I consistently deliver on time.",
        "answer_tips": [
            "Choose a real failure, not a humble brag",
            "Take ownership, don't blame others",
            "Focus heavily on what you learned",
            "Show how you've applied that learning"
        ],
        "follow_ups": [
            "How did you feel at that moment?",
            "How have you applied this learning since?",
            "What systems did you put in place?"
        ],
        "rubric": {
            "required_keywords": ["failed", "learned", "mistake", "improved"],
            "bonus_keywords": ["ownership", "growth", "applied", "changed"],
            "structure_elements": ["situation", "task", "action", "result"],
            "min_word_count": 100,
            "points_breakdown": {"honesty": 30, "learning": 40, "application": 30}
        },
        "situation_hint": "Describe the situation honestly",
        "task_hint": "What were you trying to achieve?",
        "action_hint": "What went wrong and what did you do?",
        "result_hint": "What did you learn and how did you apply it?",
        "difficulty": "medium"
    },
    {
        "question": "Describe a situation where you had to learn something new quickly.",
        "category": "Learning Agility",
        "tags": ["learning", "adaptability", "quick learner", "new skills"],
        "companies": ["Startups", "Google", "Amazon", "Razorpay", "CRED"],
        "expected_topics": ["learning", "new technology", "adaptation", "success"],
        "sample_answer": "When my team adopted React, I had no experience. I spent weekends learning, built a side project, and within a month was contributing to production code.",
        "answer_tips": [
            "Show your learning process",
            "Mention resources you used",
            "Quantify the time to proficiency",
            "Show the business impact"
        ],
        "follow_ups": [
            "What resources did you use?",
            "How do you approach learning new things?",
            "What was most challenging?"
        ],
        "rubric": {
            "required_keywords": ["learned", "new", "quickly", "result"],
            "bonus_keywords": ["resources", "practice", "applied", "contributed"],
            "structure_elements": ["situation", "task", "action", "result"],
            "min_word_count": 80,
            "points_breakdown": {"process": 35, "speed": 25, "outcome": 40}
        },
        "difficulty": "easy"
    },
    {
        "question": "Tell me about your greatest professional achievement.",
        "category": "Achievements",
        "tags": ["achievement", "success", "impact", "pride"],
        "companies": ["All companies"],
        "expected_topics": ["achievement", "impact", "metrics", "recognition"],
        "sample_answer": "I led a project that reduced API response time by 60%, resulting in 25% improvement in user engagement and was recognized with a spot award.",
        "answer_tips": [
            "Choose an achievement relevant to the role",
            "Use metrics and numbers",
            "Show your specific contribution",
            "Connect to business impact"
        ],
        "follow_ups": [
            "What was your specific role?",
            "What obstacles did you overcome?",
            "How was it received by stakeholders?"
        ],
        "rubric": {
            "required_keywords": ["achieved", "impact", "result", "led"],
            "bonus_keywords": ["metrics", "recognized", "improved", "saved"],
            "structure_elements": ["situation", "task", "action", "result"],
            "min_word_count": 100,
            "points_breakdown": {"impact": 40, "specificity": 30, "relevance": 30}
        },
        "difficulty": "easy"
    },
    {
        "question": "Describe a time when you had to persuade someone to see things your way.",
        "category": "Influence",
        "tags": ["persuasion", "influence", "communication", "leadership"],
        "companies": ["Consulting", "Product companies", "Google", "Amazon"],
        "expected_topics": ["persuasion", "data", "empathy", "outcome"],
        "sample_answer": "I proposed a new testing framework but faced resistance. I prepared data on bug reduction, showed a demo, and addressed concerns. The team adopted it and bugs reduced by 40%.",
        "answer_tips": [
            "Show you understand the other perspective",
            "Use data and evidence, not just opinion",
            "Be respectful in your approach",
            "Focus on win-win outcome"
        ],
        "follow_ups": [
            "What if they still disagreed?",
            "How did you prepare for resistance?",
            "What did you learn about persuasion?"
        ],
        "rubric": {
            "required_keywords": ["persuaded", "data", "approach", "agreed"],
            "bonus_keywords": ["understood", "evidence", "win-win", "adopted"],
            "structure_elements": ["situation", "task", "action", "result"],
            "min_word_count": 100,
            "points_breakdown": {"approach": 35, "empathy": 25, "outcome": 40}
        },
        "difficulty": "medium"
    },
    {
        "question": "Tell me about a time you took initiative beyond your job responsibilities.",
        "category": "Initiative",
        "tags": ["initiative", "proactive", "ownership", "extra mile"],
        "companies": ["Startups", "Amazon", "Google", "Flipkart"],
        "expected_topics": ["initiative", "problem identified", "action", "impact"],
        "sample_answer": "I noticed our onboarding process was slow. Without being asked, I created documentation and automated setup scripts, reducing onboarding time from 2 days to 2 hours.",
        "answer_tips": [
            "Show you identified a problem/opportunity",
            "Demonstrate self-motivation",
            "Show business impact",
            "Explain how it was received"
        ],
        "follow_ups": [
            "How was this received by your manager?",
            "What motivated you to do this?",
            "Did you continue to take similar initiatives?"
        ],
        "rubric": {
            "required_keywords": ["noticed", "initiative", "created", "improved"],
            "bonus_keywords": ["proactive", "volunteered", "impact", "recognized"],
            "structure_elements": ["situation", "task", "action", "result"],
            "min_word_count": 80,
            "points_breakdown": {"proactivity": 35, "impact": 35, "execution": 30}
        },
        "difficulty": "medium"
    },
    {
        "question": "Describe a situation where you had to work with a difficult stakeholder.",
        "category": "Stakeholder Management",
        "tags": ["stakeholder", "difficult", "communication", "patience"],
        "companies": ["Consulting", "Enterprise companies", "TCS", "Infosys"],
        "expected_topics": ["stakeholder", "communication", "patience", "resolution"],
        "sample_answer": "A client was very demanding and changed requirements frequently. I set up weekly syncs, documented everything, and proactively communicated. Eventually, they became our strongest advocate.",
        "answer_tips": [
            "Show empathy for the stakeholder's position",
            "Focus on your actions and approach",
            "Highlight communication strategies",
            "Show positive transformation"
        ],
        "follow_ups": [
            "What made them difficult?",
            "How did you maintain patience?",
            "What would you do differently?"
        ],
        "rubric": {
            "required_keywords": ["stakeholder", "communication", "resolved", "relationship"],
            "bonus_keywords": ["patience", "understood", "proactive", "advocate"],
            "structure_elements": ["situation", "task", "action", "result"],
            "min_word_count": 100,
            "points_breakdown": {"empathy": 30, "approach": 35, "outcome": 35}
        },
        "difficulty": "hard"
    },
]

TECHNICAL_QUESTIONS = [
    {
        "question": "Explain the difference between REST and GraphQL. When would you use each?",
        "category": "API Design",
        "tags": ["REST", "GraphQL", "API", "backend"],
        "companies": ["Facebook", "Shopify", "GitHub", "Hasura"],
        "expected_topics": ["REST principles", "GraphQL flexibility", "use cases", "tradeoffs"],
        "sample_answer": "REST uses multiple endpoints with fixed responses; GraphQL uses single endpoint with flexible queries. REST is simpler for CRUD; GraphQL better for complex, nested data needs.",
        "answer_tips": [
            "Explain both technologies clearly",
            "Give specific use cases for each",
            "Discuss tradeoffs objectively",
            "Mention real-world examples"
        ],
        "follow_ups": [
            "How would you handle versioning in REST?",
            "What are N+1 problems in GraphQL?",
            "How do you handle caching in each?"
        ],
        "rubric": {
            "required_keywords": ["REST", "GraphQL", "endpoint", "query"],
            "bonus_keywords": ["flexibility", "overfetching", "caching", "tradeoffs"],
            "technical_concepts": ["HTTP methods", "schema", "resolver", "mutations"],
            "min_word_count": 80,
            "points_breakdown": {"accuracy": 40, "depth": 30, "examples": 30}
        },
        "difficulty": "medium"
    },
    {
        "question": "What is database indexing and when should you use it?",
        "category": "Databases",
        "tags": ["database", "indexing", "performance", "SQL"],
        "companies": ["All tech companies"],
        "expected_topics": ["index structure", "B-tree", "when to use", "tradeoffs"],
        "sample_answer": "Indexes are data structures that speed up data retrieval by providing quick lookup paths. Use for frequently queried columns. Tradeoff: slower writes and more storage.",
        "answer_tips": [
            "Explain how indexes work (B-tree)",
            "Give examples of when to use",
            "Discuss the tradeoffs",
            "Mention composite indexes"
        ],
        "follow_ups": [
            "What is a composite index?",
            "How do you identify missing indexes?",
            "What is index bloat?"
        ],
        "rubric": {
            "required_keywords": ["index", "query", "performance", "lookup"],
            "bonus_keywords": ["B-tree", "composite", "tradeoff", "write penalty"],
            "technical_concepts": ["B-tree", "clustered", "non-clustered", "covering index"],
            "min_word_count": 80,
            "points_breakdown": {"concept": 35, "examples": 30, "tradeoffs": 35}
        },
        "difficulty": "easy"
    },
    {
        "question": "Explain microservices architecture. What are its advantages and challenges?",
        "category": "System Architecture",
        "tags": ["microservices", "architecture", "distributed systems"],
        "companies": ["Netflix", "Amazon", "Uber", "Swiggy", "Zomato"],
        "expected_topics": ["microservices", "advantages", "challenges", "when to use"],
        "sample_answer": "Microservices decompose applications into small, independent services. Advantages: scalability, independent deployment. Challenges: complexity, data consistency, network latency.",
        "answer_tips": [
            "Define microservices clearly",
            "List both advantages and challenges",
            "Give real-world examples",
            "Compare to monolithic where relevant"
        ],
        "follow_ups": [
            "How do services communicate?",
            "How do you handle data consistency?",
            "When would you choose monolith instead?"
        ],
        "rubric": {
            "required_keywords": ["microservices", "independent", "services", "scalability"],
            "bonus_keywords": ["deployment", "consistency", "communication", "complexity"],
            "technical_concepts": ["API gateway", "service mesh", "eventual consistency", "orchestration"],
            "min_word_count": 100,
            "points_breakdown": {"concept": 30, "advantages": 25, "challenges": 25, "examples": 20}
        },
        "difficulty": "medium"
    },
    {
        "question": "What is the difference between SQL and NoSQL databases?",
        "category": "Databases",
        "tags": ["SQL", "NoSQL", "database", "data modeling"],
        "companies": ["All tech companies"],
        "expected_topics": ["relational", "document", "use cases", "ACID vs BASE"],
        "sample_answer": "SQL databases are relational with fixed schemas, ACID compliant. NoSQL is flexible schema, horizontally scalable, BASE compliant. SQL for complex queries, NoSQL for scale and flexibility.",
        "answer_tips": [
            "Explain the fundamental differences",
            "Give specific database examples",
            "Discuss use cases for each",
            "Mention consistency models"
        ],
        "follow_ups": [
            "Give examples of each type",
            "When would you use MongoDB over PostgreSQL?",
            "What is eventual consistency?"
        ],
        "rubric": {
            "required_keywords": ["SQL", "NoSQL", "schema", "scalability"],
            "bonus_keywords": ["ACID", "BASE", "relational", "document"],
            "technical_concepts": ["ACID", "BASE", "CAP theorem", "sharding"],
            "min_word_count": 80,
            "points_breakdown": {"accuracy": 40, "use_cases": 30, "examples": 30}
        },
        "difficulty": "easy"
    },
    {
        "question": "Explain how HTTPS works and why it's secure.",
        "category": "Security",
        "tags": ["HTTPS", "SSL", "TLS", "security", "encryption"],
        "companies": ["All tech companies"],
        "expected_topics": ["TLS handshake", "certificates", "encryption", "authentication"],
        "sample_answer": "HTTPS uses TLS for encryption. It involves certificate verification, key exchange, and symmetric encryption. It ensures data confidentiality, integrity, and server authentication.",
        "answer_tips": [
            "Explain the TLS handshake process",
            "Discuss asymmetric vs symmetric encryption",
            "Mention certificate authorities",
            "Cover what it protects against"
        ],
        "follow_ups": [
            "What is a certificate authority?",
            "How does key exchange work?",
            "What is certificate pinning?"
        ],
        "rubric": {
            "required_keywords": ["HTTPS", "encryption", "certificate", "secure"],
            "bonus_keywords": ["TLS", "handshake", "asymmetric", "symmetric"],
            "technical_concepts": ["TLS handshake", "public key", "private key", "CA"],
            "min_word_count": 80,
            "points_breakdown": {"process": 40, "security_aspects": 30, "depth": 30}
        },
        "difficulty": "medium"
    },
    {
        "question": "What is a race condition and how do you prevent it?",
        "category": "Concurrency",
        "tags": ["race condition", "concurrency", "threading", "locks"],
        "companies": ["All tech companies"],
        "expected_topics": ["race condition", "locks", "mutex", "atomic operations"],
        "sample_answer": "Race condition occurs when multiple threads access shared data simultaneously and the outcome depends on timing. Prevent with locks, mutexes, atomic operations, or immutable data.",
        "answer_tips": [
            "Define race condition clearly",
            "Give a concrete example",
            "Discuss multiple prevention strategies",
            "Mention tradeoffs of each approach"
        ],
        "follow_ups": [
            "What is a deadlock?",
            "When would you use atomic operations vs locks?",
            "How do you debug race conditions?"
        ],
        "rubric": {
            "required_keywords": ["race condition", "threads", "shared", "lock"],
            "bonus_keywords": ["mutex", "atomic", "synchronization", "deadlock"],
            "technical_concepts": ["mutex", "semaphore", "atomic operation", "critical section"],
            "min_word_count": 80,
            "points_breakdown": {"definition": 30, "example": 30, "solutions": 40}
        },
        "difficulty": "medium"
    },
    {
        "question": "Explain the CAP theorem in distributed systems.",
        "category": "Distributed Systems",
        "tags": ["CAP theorem", "distributed", "consistency", "availability"],
        "companies": ["Google", "Amazon", "Netflix", "Uber"],
        "expected_topics": ["consistency", "availability", "partition tolerance", "tradeoffs"],
        "sample_answer": "CAP states you can only have 2 of 3: Consistency, Availability, Partition tolerance. In practice, P is required, so choose between CP (consistency) or AP (availability).",
        "answer_tips": [
            "Explain each component of CAP",
            "Explain why you can only have 2",
            "Give examples of CP and AP systems",
            "Mention modern interpretations"
        ],
        "follow_ups": [
            "Is CAP theorem still relevant?",
            "Give an example of a CP system",
            "What is eventual consistency?"
        ],
        "rubric": {
            "required_keywords": ["consistency", "availability", "partition", "CAP"],
            "bonus_keywords": ["tradeoff", "distributed", "CP", "AP"],
            "technical_concepts": ["network partition", "eventual consistency", "strong consistency"],
            "min_word_count": 80,
            "points_breakdown": {"understanding": 40, "examples": 30, "practical_application": 30}
        },
        "difficulty": "hard"
    },
    {
        "question": "What is Docker and how does it differ from virtual machines?",
        "category": "DevOps",
        "tags": ["Docker", "containers", "VM", "DevOps"],
        "companies": ["All tech companies"],
        "expected_topics": ["containers", "images", "isolation", "efficiency"],
        "sample_answer": "Docker uses containerization - sharing host OS kernel but isolating processes. VMs virtualize entire OS. Docker is lighter, faster to start, more efficient, but less isolated than VMs.",
        "answer_tips": [
            "Explain containerization concept",
            "Compare resource usage",
            "Discuss isolation levels",
            "Mention use cases for each"
        ],
        "follow_ups": [
            "What is a Docker image vs container?",
            "How does container networking work?",
            "When would you use VMs over containers?"
        ],
        "rubric": {
            "required_keywords": ["Docker", "container", "VM", "isolation"],
            "bonus_keywords": ["kernel", "image", "lightweight", "efficiency"],
            "technical_concepts": ["containerization", "namespaces", "cgroups", "hypervisor"],
            "min_word_count": 80,
            "points_breakdown": {"concept": 35, "comparison": 35, "use_cases": 30}
        },
        "difficulty": "easy"
    },
]

HR_QUESTIONS = [
    {
        "question": "Tell me about yourself.",
        "category": "Introduction",
        "tags": ["introduction", "background", "experience"],
        "companies": ["All companies"],
        "expected_topics": ["background", "experience", "skills", "goals"],
        "sample_answer": "I'm a software engineer with 3 years of experience in Python and Django. I've worked on building scalable APIs and have a passion for clean code. I'm excited about this role because...",
        "answer_tips": [
            "Keep it professional (2-3 minutes)",
            "Follow present-past-future structure",
            "Tailor to the role",
            "End with why you're interested"
        ],
        "follow_ups": [
            "Why did you choose this career?",
            "What are you most proud of?",
            "Where do you see yourself in 5 years?"
        ],
        "rubric": {
            "required_keywords": ["experience", "skills", "role", "interested"],
            "bonus_keywords": ["passion", "growth", "achievements", "goals"],
            "min_word_count": 100,
            "points_breakdown": {"structure": 30, "relevance": 40, "enthusiasm": 30}
        },
        "difficulty": "easy"
    },
    {
        "question": "Why do you want to work at our company?",
        "category": "Motivation",
        "tags": ["motivation", "company research", "fit"],
        "companies": ["All companies"],
        "expected_topics": ["company knowledge", "alignment", "contribution", "growth"],
        "sample_answer": "I admire your company's commitment to [specific value]. Your work on [specific product] aligns with my experience in [relevant area]. I believe I can contribute to [specific goal].",
        "answer_tips": [
            "Research the company thoroughly",
            "Mention specific products/values",
            "Connect your skills to their needs",
            "Show genuine enthusiasm"
        ],
        "follow_ups": [
            "What do you know about our products?",
            "How did you hear about us?",
            "What other companies are you interviewing with?"
        ],
        "rubric": {
            "required_keywords": ["company", "role", "contribute", "excited"],
            "bonus_keywords": ["research", "values", "growth", "mission"],
            "min_word_count": 80,
            "points_breakdown": {"research": 40, "alignment": 30, "enthusiasm": 30}
        },
        "difficulty": "easy"
    },
    {
        "question": "What are your salary expectations?",
        "category": "Compensation",
        "tags": ["salary", "negotiation", "compensation"],
        "companies": ["All companies"],
        "expected_topics": ["research", "range", "flexibility", "value"],
        "sample_answer": "Based on my research and experience, I'm looking for a range of ₹X to ₹Y LPA. However, I'm flexible and more interested in the overall opportunity and growth potential.",
        "answer_tips": [
            "Research market rates beforehand",
            "Give a range, not a fixed number",
            "Show flexibility",
            "Focus on value, not just money"
        ],
        "follow_ups": [
            "Is that negotiable?",
            "What's your current salary?",
            "What's most important to you in compensation?"
        ],
        "rubric": {
            "required_keywords": ["range", "research", "experience", "flexible"],
            "bonus_keywords": ["value", "growth", "opportunity", "market"],
            "min_word_count": 50,
            "points_breakdown": {"preparation": 40, "professionalism": 30, "flexibility": 30}
        },
        "difficulty": "medium"
    },
    {
        "question": "What are your strengths and weaknesses?",
        "category": "Self-Awareness",
        "tags": ["strengths", "weaknesses", "self-awareness"],
        "companies": ["All companies"],
        "expected_topics": ["honest assessment", "examples", "improvement"],
        "sample_answer": "My strength is problem-solving - I enjoy breaking down complex issues. My weakness is public speaking, but I've been improving by volunteering for presentations.",
        "answer_tips": [
            "Be honest but strategic",
            "Give examples for strengths",
            "Show improvement efforts for weaknesses",
            "Don't use clichés like 'perfectionist'"
        ],
        "follow_ups": [
            "Can you give an example of using that strength?",
            "How are you working on that weakness?",
            "What feedback have you received?"
        ],
        "rubric": {
            "required_keywords": ["strength", "weakness", "example", "improving"],
            "bonus_keywords": ["feedback", "working on", "developed", "growth"],
            "min_word_count": 80,
            "points_breakdown": {"honesty": 30, "examples": 35, "improvement": 35}
        },
        "difficulty": "easy"
    },
    {
        "question": "Why are you leaving your current job?",
        "category": "Career Transition",
        "tags": ["leaving", "transition", "growth"],
        "companies": ["All companies"],
        "expected_topics": ["growth", "opportunity", "positive framing"],
        "sample_answer": "I've learned a lot at my current role, but I'm looking for new challenges and growth opportunities. This role offers the chance to work on larger scale systems.",
        "answer_tips": [
            "Stay positive - don't criticize current employer",
            "Focus on what you're moving toward",
            "Show logical career progression",
            "Be honest but diplomatic"
        ],
        "follow_ups": [
            "What would make you stay at your current job?",
            "What's missing in your current role?",
            "How would this role address that?"
        ],
        "rubric": {
            "required_keywords": ["growth", "opportunity", "challenge", "looking for"],
            "bonus_keywords": ["learned", "progression", "excited", "new"],
            "min_word_count": 60,
            "points_breakdown": {"positivity": 35, "logic": 35, "honesty": 30}
        },
        "difficulty": "medium"
    },
    {
        "question": "Do you have any questions for us?",
        "category": "Engagement",
        "tags": ["questions", "curiosity", "engagement"],
        "companies": ["All companies"],
        "expected_topics": ["thoughtful questions", "role clarity", "culture"],
        "sample_answer": "Yes! 1) What does success look like in the first 90 days? 2) How does the team handle technical decisions? 3) What's the biggest challenge the team is facing?",
        "answer_tips": [
            "Always have 3-5 questions prepared",
            "Ask about role, team, culture, growth",
            "Show genuine curiosity",
            "Avoid salary questions in early rounds"
        ],
        "follow_ups": [],
        "rubric": {
            "required_keywords": ["question", "team", "role", "how"],
            "bonus_keywords": ["success", "growth", "culture", "challenges"],
            "min_word_count": 40,
            "points_breakdown": {"quality": 50, "curiosity": 30, "preparation": 20}
        },
        "difficulty": "easy"
    },
]

SYSTEM_DESIGN_QUESTIONS = [
    {
        "question": "Design a URL shortener like bit.ly.",
        "category": "System Design",
        "tags": ["URL shortener", "hashing", "database", "scalability"],
        "companies": ["Google", "Amazon", "Microsoft", "Uber"],
        "expected_topics": ["hashing", "database choice", "scalability", "analytics"],
        "sample_answer": "Use base62 encoding for short URLs, distributed key-value store for storage, cache for popular URLs, and analytics service for tracking. Handle collision with retry.",
        "answer_tips": [
            "Start with requirements clarification",
            "Discuss API design",
            "Cover storage and encoding",
            "Address scalability and caching"
        ],
        "follow_ups": [
            "How do you handle collisions?",
            "How would you scale to 100M URLs?",
            "How do you handle expired URLs?"
        ],
        "rubric": {
            "required_keywords": ["hash", "database", "API", "scale"],
            "bonus_keywords": ["cache", "collision", "base62", "analytics"],
            "technical_concepts": ["base62", "consistent hashing", "caching", "sharding"],
            "min_word_count": 150,
            "points_breakdown": {"requirements": 20, "design": 40, "scalability": 25, "tradeoffs": 15}
        },
        "difficulty": "medium"
    },
    {
        "question": "Design a rate limiter for an API.",
        "category": "System Design",
        "tags": ["rate limiting", "API", "distributed systems"],
        "companies": ["Stripe", "Razorpay", "Google", "Amazon"],
        "expected_topics": ["algorithms", "distributed rate limiting", "storage", "rules"],
        "sample_answer": "Use token bucket or sliding window algorithm. Store counters in Redis for distributed systems. Support multiple rules (per user, IP, endpoint). Return 429 with retry-after header.",
        "answer_tips": [
            "Discuss different algorithms (token bucket, sliding window)",
            "Cover distributed rate limiting",
            "Address rule configuration",
            "Handle edge cases"
        ],
        "follow_ups": [
            "Token bucket vs sliding window?",
            "How to rate limit in distributed system?",
            "How to handle burst traffic?"
        ],
        "rubric": {
            "required_keywords": ["rate limit", "algorithm", "distributed", "Redis"],
            "bonus_keywords": ["token bucket", "sliding window", "429", "retry"],
            "technical_concepts": ["token bucket", "sliding window", "Redis", "atomic operations"],
            "min_word_count": 150,
            "points_breakdown": {"algorithm": 35, "implementation": 30, "distributed": 25, "edge_cases": 10}
        },
        "difficulty": "medium"
    },
    {
        "question": "Design a notification system (push, email, SMS).",
        "category": "System Design",
        "tags": ["notifications", "push", "email", "SMS", "queues"],
        "companies": ["Uber", "Swiggy", "Zomato", "Amazon"],
        "expected_topics": ["channels", "message queue", "templates", "preferences"],
        "sample_answer": "Use message queue (Kafka/SQS) for async processing. Separate handlers for each channel. Template service for content. User preferences for channel selection. Retry with exponential backoff.",
        "answer_tips": [
            "Discuss different notification channels",
            "Cover async processing with queues",
            "Address user preferences",
            "Handle failures and retries"
        ],
        "follow_ups": [
            "How do you handle notification preferences?",
            "How do you ensure delivery?",
            "How do you handle rate limiting for SMS?"
        ],
        "rubric": {
            "required_keywords": ["queue", "channels", "async", "retry"],
            "bonus_keywords": ["preferences", "template", "exponential backoff", "delivery"],
            "technical_concepts": ["message queue", "pub/sub", "push notifications", "webhooks"],
            "min_word_count": 150,
            "points_breakdown": {"architecture": 35, "channels": 25, "reliability": 25, "preferences": 15}
        },
        "difficulty": "medium"
    },
]

# Combine all questions
ALL_QUESTIONS = {
    "behavioral": BEHAVIORAL_QUESTIONS,
    "technical": TECHNICAL_QUESTIONS,
    "hr": HR_QUESTIONS,
    "system_design": SYSTEM_DESIGN_QUESTIONS,
}


# =============================================================================
# Interview Question Bank Class
# =============================================================================

class InterviewQuestionBank:
    """
    Manages interview question bank.
    No LLM dependency - loads questions from database.
    
    Database-backed implementation that reads from InterviewQuestion model.
    Falls back to hardcoded questions if database is empty.
    """
    
    def __init__(self, use_database: bool = True):
        """
        Initialize the question bank.
        
        Args:
            use_database: If True, load from database. If False, use hardcoded questions.
        """
        self.use_database = use_database
        self.data_dir = Path(__file__).parent.parent.parent / "data" / "interview_bank"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._questions_cache = None  # Lazy loading
    
    @property
    def questions(self) -> List[Dict[str, Any]]:
        """Load questions lazily."""
        if self._questions_cache is None:
            self._questions_cache = self._load_all_questions()
        return self._questions_cache
    
    def _load_all_questions(self) -> List[Dict[str, Any]]:
        """Load all questions from database or fallback to hardcoded."""
        if self.use_database:
            try:
                return self._load_from_database()
            except Exception as e:
                logger.warning(f"Could not load from database: {e}. Using hardcoded questions.")
                return self._load_from_hardcoded()
        return self._load_from_hardcoded()
    
    def _load_from_database(self) -> List[Dict[str, Any]]:
        """Load questions from the InterviewQuestion model."""
        # Import here to avoid circular imports
        from apps.interview.models import InterviewQuestion
        
        questions = InterviewQuestion.objects.filter(is_active=True)
        
        if not questions.exists():
            logger.info("No questions in database. Using hardcoded questions.")
            return self._load_from_hardcoded()
        
        all_questions = []
        for idx, q in enumerate(questions, 1):
            all_questions.append({
                "id": str(q.id),  # UUID as string
                "db_id": q.id,   # Original UUID for DB operations
                "question": q.question,
                "question_type": q.question_type,
                "category": q.category,
                "difficulty": q.difficulty,
                "tags": q.tags or [],
                "companies": q.companies or [],
                "expected_topics": q.expected_topics or [],
                "sample_answer": q.sample_answer or "",
                "answer_tips": q.answer_tips or [],
                "follow_ups": [],  # Not stored in DB yet
                "rubric": self._build_rubric_from_question(q),
                "situation_hint": q.situation_hint or "",
                "task_hint": q.task_hint or "",
                "action_hint": q.action_hint or "",
                "result_hint": q.result_hint or "",
            })
        
        logger.info(f"Loaded {len(all_questions)} questions from database")
        return all_questions
    
    def _build_rubric_from_question(self, question) -> Dict[str, Any]:
        """Build evaluation rubric from question data."""
        rubric = {
            "required_keywords": question.expected_topics or [],
            "bonus_keywords": question.tags or [],
            "min_word_count": 50,
            "max_word_count": 500,
            "structure_elements": [],
            "points_breakdown": {}
        }
        
        # Check if this is an HR-type question (mapped to behavioral but not STAR-style)
        hr_categories = ["Introduction", "Motivation", "Compensation", "Self-Assessment", 
                         "Career Goals", "Career Transition", "Work Style", "Culture Fit",
                         "Company Research", "Continuous Learning", "Engagement", "Logistics",
                         "Value Proposition", "Achievement", "Self-Improvement"]
        hr_question_patterns = ["tell me about yourself", "why do you want", "salary",
                                "strength", "weakness", "5 years", "leaving", "motivates",
                                "describe your ideal", "what do you know about"]
        
        is_hr_style = (
            question.category in hr_categories or
            any(pattern in question.question.lower() for pattern in hr_question_patterns)
        )
        
        # Add STAR structure for behavioral questions (but not HR-style)
        if question.question_type == "behavioral" and not is_hr_style:
            rubric["structure_elements"] = ["situation", "task", "action", "result"]
            rubric["points_breakdown"] = {
                "structure": 30,
                "content": 40,
                "specificity": 30
            }
        elif question.question_type == "behavioral" and is_hr_style:
            # HR-style questions focus on content and clarity, not STAR
            rubric["points_breakdown"] = {
                "content": 50,
                "clarity": 30,
                "relevance": 20
            }
        elif question.question_type == "technical":
            rubric["points_breakdown"] = {
                "accuracy": 40,
                "depth": 30,
                "examples": 30
            }
        elif question.question_type == "system_design":
            rubric["min_word_count"] = 100
            rubric["points_breakdown"] = {
                "approach": 30,
                "depth": 40,
                "examples": 30
            }
        
        return rubric
    
    def _load_from_hardcoded(self) -> List[Dict[str, Any]]:
        """Load questions from hardcoded banks (fallback)."""
        all_questions = []
        question_id = 0
        
        for q_type, questions in ALL_QUESTIONS.items():
            for q in questions:
                question_id += 1
                all_questions.append({
                    "id": question_id,
                    "question": q["question"],
                    "question_type": q_type,
                    "category": q["category"],
                    "difficulty": q.get("difficulty", "medium"),
                    "tags": q.get("tags", []),
                    "companies": q.get("companies", []),
                    "expected_topics": q.get("expected_topics", []),
                    "sample_answer": q.get("sample_answer", ""),
                    "answer_tips": q.get("answer_tips", []),
                    "follow_ups": q.get("follow_ups", []),
                    "rubric": q.get("rubric", {}),
                    "situation_hint": q.get("situation_hint", ""),
                    "task_hint": q.get("task_hint", ""),
                    "action_hint": q.get("action_hint", ""),
                    "result_hint": q.get("result_hint", ""),
                })
        
        return all_questions
    
    def refresh_cache(self):
        """Force reload questions from database."""
        self._questions_cache = None
        return len(self.questions)
    
    def get_questions(
        self,
        question_type: Optional[str] = None,
        difficulty: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 10,
        exclude_ids: List = None
    ) -> List[Dict[str, Any]]:
        """Get filtered questions."""
        filtered = self.questions.copy()
        
        if question_type:
            filtered = [q for q in filtered if q["question_type"] == question_type]
        
        if difficulty:
            filtered = [q for q in filtered if q["difficulty"] == difficulty]
        
        if category:
            filtered = [q for q in filtered if q["category"].lower() == category.lower()]
        
        if exclude_ids:
            # Convert to strings for comparison
            exclude_str_ids = [str(eid) for eid in exclude_ids]
            filtered = [q for q in filtered if str(q["id"]) not in exclude_str_ids]
        
        if len(filtered) > limit:
            filtered = random.sample(filtered, limit)
        
        return filtered
    
    def get_question_by_id(self, question_id) -> Optional[Dict[str, Any]]:
        """Get specific question by ID (supports UUID strings and integers)."""
        # Convert to string for comparison
        str_id = str(question_id)
        
        for q in self.questions:
            # Compare as strings to handle both UUID and int IDs
            if str(q["id"]) == str_id:
                return q
        return None
    
    def get_questions_by_company(
        self,
        company: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get questions known to be asked at a specific company."""
        filtered = [
            q for q in self.questions 
            if company.lower() in [c.lower() for c in q["companies"]]
        ]
        
        if len(filtered) > limit:
            filtered = random.sample(filtered, limit)
        
        return filtered
    
    def get_questions_for_role(
        self,
        role: str,
        include_behavioral: bool = True,
        include_technical: bool = True,
        include_hr: bool = True,
        num_questions: int = 10
    ) -> List[Dict[str, Any]]:
        """Get mixed questions for a specific role."""
        result = []
        
        # Determine distribution based on role
        if "engineer" in role.lower() or "developer" in role.lower():
            distribution = {"technical": 0.5, "behavioral": 0.3, "hr": 0.2}
        elif "manager" in role.lower():
            distribution = {"behavioral": 0.5, "hr": 0.3, "technical": 0.2}
        else:
            distribution = {"behavioral": 0.4, "technical": 0.3, "hr": 0.3}
        
        for q_type, ratio in distribution.items():
            count = max(1, int(num_questions * ratio))
            questions = self.get_questions(question_type=q_type, limit=count)
            result.extend(questions)
        
        random.shuffle(result)
        return result[:num_questions]
    
    def save_to_json(self, filename: str = "interview_bank.json"):
        """Save questions to JSON file."""
        filepath = self.data_dir / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.questions, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved {len(self.questions)} questions to {filepath}")
        return filepath
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the question bank."""
        stats = {
            "total_questions": len(self.questions),
            "by_type": {},
            "by_difficulty": {},
            "by_category": {},
        }
        
        for q in self.questions:
            # By type
            q_type = q["question_type"]
            stats["by_type"][q_type] = stats["by_type"].get(q_type, 0) + 1
            
            # By difficulty
            diff = q["difficulty"]
            stats["by_difficulty"][diff] = stats["by_difficulty"].get(diff, 0) + 1
            
            # By category
            cat = q["category"]
            stats["by_category"][cat] = stats["by_category"].get(cat, 0) + 1
        
        return stats
    
    def evaluate_response(
        self,
        question: str,
        answer: str,
        question_type: str = "behavioral"
    ) -> Dict[str, Any]:
        """
        Evaluate an interview response using rubric-based scoring.
        
        This method:
        1. Finds the matching question in the bank (by text similarity)
        2. Applies rubric-based evaluation (keyword matching, STAR method, etc.)
        3. Returns scores and feedback
        
        Args:
            question: The interview question text
            answer: The candidate's response
            question_type: Type of question (behavioral, technical, hr, etc.)
            
        Returns:
            Dictionary with scores, feedback, and analysis
        """
        # Find matching question in bank
        matched_question = self._find_question_by_text(question, question_type)
        
        if not matched_question:
            # Fall back to generic evaluation
            return self._generic_evaluation(answer, question_type)
        
        # Build rubric from matched question
        rubric = matched_question.get("rubric", {})
        expected_topics = matched_question.get("expected_topics", [])
        sample_answer = matched_question.get("sample_answer", "")
        answer_tips = matched_question.get("answer_tips", [])
        
        # Update rubric with expected topics if not already present
        if expected_topics and not rubric.get("required_keywords"):
            rubric["required_keywords"] = expected_topics
        
        # Perform evaluation
        return self._evaluate_with_rubric(answer, rubric, matched_question)
    
    def _find_question_by_text(
        self,
        question_text: str,
        question_type: str = None
    ) -> Optional[Dict[str, Any]]:
        """Find a question by text similarity."""
        question_lower = question_text.lower().strip()
        
        # Try with type filter first, then without
        for candidates in [
            [q for q in self.questions if q["question_type"] == question_type] if question_type else self.questions,
            self.questions  # Fallback to all questions
        ]:
            if not candidates:
                continue
                
            # Exact match first
            for q in candidates:
                if q["question"].lower().strip() == question_lower:
                    return q
            
            # Partial match (first 50 chars)
            question_prefix = question_lower[:50]
            for q in candidates:
                if q["question"].lower()[:50] == question_prefix:
                    return q
            
            # Keyword-based match
            question_words = set(question_lower.split())
            best_match = None
            best_score = 0
            
            for q in candidates:
                q_words = set(q["question"].lower().split())
                common = len(question_words & q_words)
                score = common / max(len(question_words), 1)
                
                if score > best_score and score > 0.5:  # At least 50% word overlap
                    best_score = score
                    best_match = q
            
            if best_match:
                return best_match
        
        return None
    
    def _generic_evaluation(
        self,
        answer: str,
        question_type: str
    ) -> Dict[str, Any]:
        """Generic evaluation when no matching question found."""
        words = answer.split()
        word_count = len(words)
        
        # Basic scoring
        scores = {
            "overall_score": 50,
            "content_score": 50,
            "structure_score": 50,
            "clarity_score": 50,
            "relevance_score": 50
        }
        
        # Adjust based on length
        if word_count < 30:
            scores["content_score"] = 30
            scores["overall_score"] = 35
        elif word_count > 50:
            scores["content_score"] = 60
            scores["overall_score"] = 55
        
        if word_count > 100:
            scores["structure_score"] = 60
            scores["overall_score"] = 60
        
        return {
            **scores,
            "feedback": "Response evaluated with basic metrics. Add more specific details and structure your answer clearly.",
            "matched_keywords": [],
            "structure_analysis": "Generic analysis - no matching question found",
            "length_assessment": "appropriate" if 50 <= word_count <= 300 else "needs adjustment",
            "improvement_suggestions": [
                "Add specific examples from your experience",
                "Use the STAR method for behavioral questions",
                "Include relevant metrics or outcomes"
            ],
            "strengths": ["Response provided"],
            "areas_to_improve": ["Add more specificity", "Include concrete examples"],
            "star_analysis": {},
            "evaluation_method": "generic_fallback"
        }
    
    def _evaluate_with_rubric(
        self,
        answer: str,
        rubric: Dict[str, Any],
        question: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Evaluate answer using rubric-based scoring."""
        answer_lower = answer.lower()
        words = answer.split()
        word_count = len(words)
        
        # Initialize scores
        scores = {
            "overall_score": 50,
            "content_score": 50,
            "structure_score": 50,
            "clarity_score": 50,
            "relevance_score": 50
        }
        
        matched_keywords = []
        missing_keywords = []
        strengths = []
        improvements = []
        
        # 1. Keyword Analysis
        required_keywords = rubric.get("required_keywords", [])
        bonus_keywords = rubric.get("bonus_keywords", question.get("tags", []))
        
        for kw in required_keywords:
            if kw.lower() in answer_lower:
                matched_keywords.append(kw)
            else:
                missing_keywords.append(kw)
        
        for kw in bonus_keywords:
            if kw.lower() in answer_lower and kw not in matched_keywords:
                matched_keywords.append(kw)
        
        if required_keywords:
            keyword_ratio = len(matched_keywords) / len(required_keywords)
            scores["relevance_score"] = min(100, int(keyword_ratio * 80) + 20)
        
        if matched_keywords:
            strengths.append(f"Good coverage of key topics: {', '.join(matched_keywords[:3])}")
        if missing_keywords:
            improvements.append(f"Consider addressing: {', '.join(missing_keywords[:3])}")
        
        # 2. Structure Analysis (STAR method for behavioral)
        structure_elements = rubric.get("structure_elements", [])
        star_analysis = {}
        
        if structure_elements:
            found_elements = 0
            
            situation_patterns = ["when", "at my", "during", "situation", "in my role", "while working"]
            task_patterns = ["needed to", "had to", "responsible for", "challenge was", "goal was", "task"]
            action_patterns = ["i did", "i took", "i decided", "i implemented", "action", "approached", "created", "developed"]
            result_patterns = ["result", "outcome", "achieved", "improved", "reduced", "increased", "%", "success"]
            
            if any(p in answer_lower for p in situation_patterns):
                found_elements += 1
                star_analysis["situation"] = "Present"
            else:
                star_analysis["situation"] = "Missing"
            
            if any(p in answer_lower for p in task_patterns):
                found_elements += 1
                star_analysis["task"] = "Present"
            else:
                star_analysis["task"] = "Missing"
            
            if any(p in answer_lower for p in action_patterns):
                found_elements += 1
                star_analysis["action"] = "Present"
            else:
                star_analysis["action"] = "Missing"
            
            if any(p in answer_lower for p in result_patterns):
                found_elements += 1
                star_analysis["result"] = "Present"
            else:
                star_analysis["result"] = "Missing"
            
            scores["structure_score"] = int((found_elements / 4) * 100)
            
            if found_elements >= 4:
                strengths.append("Excellent use of STAR method")
            elif found_elements >= 2:
                strengths.append("Good structure, but could be more complete")
            else:
                improvements.append("Use the STAR method: Situation, Task, Action, Result")
        else:
            # Technical/coding questions - different structure
            if "because" in answer_lower or "for example" in answer_lower:
                scores["structure_score"] = 70
                strengths.append("Good explanation with reasoning")
            
            if "first" in answer_lower or "then" in answer_lower or "finally" in answer_lower:
                scores["structure_score"] = min(100, scores["structure_score"] + 15)
        
        # 3. Length Analysis
        min_words = rubric.get("min_word_count", 50)
        max_words = rubric.get("max_word_count", 500)
        
        length_assessment = "appropriate"
        if word_count < min_words:
            scores["content_score"] = max(30, int(50 * (word_count / min_words)))
            length_assessment = "too brief"
            improvements.append(f"Provide more detail (aim for at least {min_words} words)")
        elif word_count > max_words:
            scores["content_score"] = 70
            length_assessment = "too long"
            improvements.append("Try to be more concise while keeping key points")
        else:
            scores["content_score"] = min(100, 60 + int((word_count - min_words) / (max_words - min_words) * 40))
            if word_count >= min_words * 1.5:
                strengths.append("Good level of detail")
        
        # 4. Clarity Analysis (sentence structure, filler words)
        filler_patterns = ["um", "uh", "like", "you know", "basically", "actually"]
        filler_count = sum(1 for p in filler_patterns if p in answer_lower)
        
        avg_sentence_length = word_count / max(1, answer.count('.') + answer.count('!') + answer.count('?'))
        
        if filler_count > 3:
            scores["clarity_score"] = 50
            improvements.append("Reduce filler words for clearer communication")
        elif avg_sentence_length > 40:
            scores["clarity_score"] = 60
            improvements.append("Break long sentences into shorter ones")
        else:
            scores["clarity_score"] = 80
            if filler_count == 0:
                strengths.append("Clear and professional communication")
        
        # 5. Calculate Overall Score
        weights = {"content": 0.3, "structure": 0.25, "clarity": 0.2, "relevance": 0.25}
        scores["overall_score"] = int(
            scores["content_score"] * weights["content"] +
            scores["structure_score"] * weights["structure"] +
            scores["clarity_score"] * weights["clarity"] +
            scores["relevance_score"] * weights["relevance"]
        )
        
        # Generate feedback
        if scores["overall_score"] >= 80:
            feedback = "Excellent response! You covered key points effectively with good structure and clarity."
        elif scores["overall_score"] >= 60:
            feedback = "Good response with strong fundamentals. Focus on the suggested improvements for an even better answer."
        elif scores["overall_score"] >= 40:
            feedback = "Adequate response but needs more structure and detail. Review the improvement suggestions."
        else:
            feedback = "Response needs significant improvement. Focus on adding specific examples and better structure."
        
        return {
            "overall_score": scores["overall_score"],
            "content_score": scores["content_score"],
            "structure_score": scores["structure_score"],
            "clarity_score": scores["clarity_score"],
            "relevance_score": scores["relevance_score"],
            "feedback": feedback,
            "matched_keywords": matched_keywords,
            "missing_keywords": missing_keywords,
            "structure_analysis": star_analysis if star_analysis else "N/A for this question type",
            "length_assessment": length_assessment,
            "word_count": word_count,
            "improvement_suggestions": improvements,
            "strengths": strengths,
            "areas_to_improve": improvements,
            "star_analysis": star_analysis,
            "evaluation_method": "llm_free_rubric",
            "sample_answer": question.get("sample_answer", ""),
            "answer_tips": question.get("answer_tips", [])
        }

class ResponseEvaluator:
    """
    Evaluates interview responses using rubrics.
    No LLM dependency - pure algorithmic evaluation.
    
    Scoring components:
    1. Keyword matching (required + bonus)
    2. Structure analysis (STAR method)
    3. Length and detail
    4. Technical accuracy (for technical questions)
    """
    
    def __init__(self):
        self.question_bank = InterviewQuestionBank()
    
    def evaluate_response(
        self,
        question_id,  # Can be int or UUID string
        response: str,
        question_type: str = None
    ) -> Dict[str, Any]:
        """
        Evaluate an interview response.
        
        Returns:
            {
                "score": 0-100,
                "breakdown": {...},
                "feedback": [...],
                "strengths": [...],
                "improvements": [...],
                "keywords_found": [...],
                "keywords_missing": [...]
            }
        """
        question = self.question_bank.get_question_by_id(question_id)
        if not question:
            return {"error": "Question not found", "score": 0}
        
        rubric = question.get("rubric", {})
        response_lower = response.lower()
        words = response.split()
        word_count = len(words)
        
        # Initialize scores
        scores = {
            "keyword_score": 0,
            "structure_score": 0,
            "length_score": 0,
            "detail_score": 0,
        }
        
        feedback = []
        strengths = []
        improvements = []
        
        # 1. Keyword Analysis
        required_keywords = rubric.get("required_keywords", [])
        bonus_keywords = rubric.get("bonus_keywords", [])
        
        found_required = [kw for kw in required_keywords if kw.lower() in response_lower]
        found_bonus = [kw for kw in bonus_keywords if kw.lower() in response_lower]
        missing_required = [kw for kw in required_keywords if kw.lower() not in response_lower]
        
        if required_keywords:
            scores["keyword_score"] = (len(found_required) / len(required_keywords)) * 70
            scores["keyword_score"] += (len(found_bonus) / max(len(bonus_keywords), 1)) * 30
        else:
            scores["keyword_score"] = 50  # No rubric, neutral score
        
        if missing_required:
            improvements.append(f"Consider mentioning: {', '.join(missing_required[:3])}")
        if found_bonus:
            strengths.append(f"Good use of relevant terms: {', '.join(found_bonus[:3])}")
        
        # 2. Structure Analysis (for behavioral questions)
        structure_elements = rubric.get("structure_elements", [])
        if structure_elements:
            found_elements = 0
            for element in structure_elements:
                if element == "situation" and any(kw in response_lower for kw in ["when", "at", "during", "situation"]):
                    found_elements += 1
                elif element == "task" and any(kw in response_lower for kw in ["needed", "had to", "responsible", "task"]):
                    found_elements += 1
                elif element == "action" and any(kw in response_lower for kw in ["i did", "i took", "i decided", "action", "i implemented"]):
                    found_elements += 1
                elif element == "result" and any(kw in response_lower for kw in ["result", "outcome", "achieved", "improved", "%", "reduced"]):
                    found_elements += 1
            
            scores["structure_score"] = (found_elements / len(structure_elements)) * 100
            
            if found_elements < len(structure_elements):
                improvements.append("Use STAR method: Situation, Task, Action, Result")
            else:
                strengths.append("Good use of STAR method structure")
        else:
            scores["structure_score"] = 50  # No structure requirement
        
        # 3. Length Analysis
        min_words = rubric.get("min_word_count", 50)
        max_words = rubric.get("max_word_count", 500)
        
        if word_count < min_words:
            scores["length_score"] = (word_count / min_words) * 60
            improvements.append(f"Response is too brief. Aim for at least {min_words} words.")
        elif word_count > max_words:
            scores["length_score"] = 70  # Penalty for being too long
            improvements.append(f"Response is too long. Try to be more concise.")
        else:
            scores["length_score"] = 100
            if word_count >= min_words * 1.5:
                strengths.append("Good level of detail in response")
        
        # 4. Detail Analysis (looking for specifics)
        detail_indicators = [
            (r'\d+%', "percentages"),
            (r'\d+ (days|weeks|months|years)', "time metrics"),
            (r'₹[\d,]+|\$[\d,]+', "financial impact"),
            (r'(increased|decreased|improved|reduced) by', "impact statements"),
            (r'(specifically|for example|such as)', "examples"),
        ]
        
        detail_count = 0
        for pattern, indicator in detail_indicators:
            if re.search(pattern, response_lower):
                detail_count += 1
        
        scores["detail_score"] = min(100, detail_count * 25)
        
        if detail_count >= 3:
            strengths.append("Excellent use of specific details and metrics")
        elif detail_count == 0:
            improvements.append("Add specific examples, numbers, or metrics")
        
        # Calculate final score
        points_breakdown = rubric.get("points_breakdown", {})
        if points_breakdown:
            # Weighted average based on rubric
            total_weight = sum(points_breakdown.values())
            weighted_score = 0
            
            # Map rubric keys to our scores
            score_mapping = {
                "structure": scores["structure_score"],
                "content": scores["keyword_score"],
                "specificity": scores["detail_score"],
                "honesty": scores["keyword_score"],  # Approximation
                "learning": scores["detail_score"],
                "application": scores["structure_score"],
                "process": scores["structure_score"],
                "speed": scores["length_score"],
                "outcome": scores["detail_score"],
                "impact": scores["detail_score"],
                "relevance": scores["keyword_score"],
                "approach": scores["structure_score"],
                "empathy": scores["keyword_score"],
                "emotional_intelligence": scores["keyword_score"],
                "proactivity": scores["keyword_score"],
                "execution": scores["structure_score"],
                "accuracy": scores["keyword_score"],
                "depth": scores["detail_score"],
                "examples": scores["detail_score"],
            }
            
            for key, weight in points_breakdown.items():
                score = score_mapping.get(key, 50)  # Default to 50 if key not found
                weighted_score += (score * weight / total_weight)
            
            final_score = weighted_score
        else:
            # Simple average
            final_score = sum(scores.values()) / len(scores)
        
        # Generate overall feedback
        if final_score >= 80:
            feedback.append("Excellent response! You covered the key points effectively.")
        elif final_score >= 60:
            feedback.append("Good response with room for improvement.")
        elif final_score >= 40:
            feedback.append("Adequate response but needs more detail and structure.")
        else:
            feedback.append("Response needs significant improvement. Focus on the STAR method.")
        
        return {
            "score": round(final_score, 1),
            "breakdown": {k: round(v, 1) for k, v in scores.items()},
            "feedback": feedback,
            "strengths": strengths,
            "improvements": improvements,
            "keywords_found": found_required + found_bonus,
            "keywords_missing": missing_required,
            "word_count": word_count,
            "tips": question.get("answer_tips", []),
            "sample_answer": question.get("sample_answer", ""),
        }
    
    def get_follow_up_questions(self, question_id: int) -> List[str]:
        """Get follow-up questions for a given question."""
        question = self.question_bank.get_question_by_id(question_id)
        if question:
            return question.get("follow_ups", [])
        return []
    
    def get_star_hints(self, question_id: int) -> Dict[str, str]:
        """Get STAR method hints for behavioral questions."""
        question = self.question_bank.get_question_by_id(question_id)
        if question:
            return {
                "situation": question.get("situation_hint", ""),
                "task": question.get("task_hint", ""),
                "action": question.get("action_hint", ""),
                "result": question.get("result_hint", ""),
            }
        return {}


# =============================================================================
# Factory Functions
# =============================================================================

def get_interview_question_bank() -> InterviewQuestionBank:
    """Get interview question bank instance."""
    return InterviewQuestionBank()


def get_response_evaluator() -> ResponseEvaluator:
    """Get response evaluator instance."""
    return ResponseEvaluator()
