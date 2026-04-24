"""
Interview Coach Service
========================
AI-powered interview preparation and coaching.

Features:
1. Role-specific question generation
2. Behavioral and technical questions
3. Answer evaluation and feedback
4. Mock interview sessions
5. STAR method coaching
"""

import logging
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from services.ai.base import get_ai_service, AIResponse

logger = logging.getLogger(__name__)


# Interview question bank by category
QUESTION_BANK = {
    "behavioral": {
        "teamwork": [
            "Tell me about a time you worked on a challenging team project. What was your role?",
            "Describe a situation where you had to collaborate with a difficult colleague.",
            "Give an example of when you helped a team member who was struggling.",
            "Tell me about a time when your team failed to meet a goal. What happened?",
        ],
        "leadership": [
            "Describe a time when you took the lead on a project without being asked.",
            "Tell me about a situation where you had to motivate others.",
            "Give an example of when you had to make an unpopular decision.",
            "How have you handled mentoring or training junior team members?",
        ],
        "problem_solving": [
            "Describe a complex problem you solved. What was your approach?",
            "Tell me about a time when you had to make a decision with incomplete information.",
            "Give an example of when you identified a problem before others noticed.",
            "How do you approach debugging a difficult issue?",
        ],
        "conflict": [
            "Tell me about a disagreement with a coworker. How did you resolve it?",
            "Describe a time when you received harsh criticism. How did you respond?",
            "Give an example of when you had to push back on a stakeholder request.",
        ],
        "failure": [
            "Tell me about a project that didn't go as planned. What did you learn?",
            "Describe a mistake you made and how you handled it.",
            "Give an example of a goal you didn't achieve. What happened?",
        ],
    },
    "technical_software": {
        "system_design": [
            "How would you design a URL shortening service like bit.ly?",
            "Design a rate limiter for an API. What data structures would you use?",
            "How would you design a chat application that scales to millions of users?",
            "Design a notification system for a social media platform.",
            "How would you architect a file storage service like Dropbox?",
        ],
        "coding_concepts": [
            "Explain the difference between a stack and a queue. When would you use each?",
            "What is the time complexity of binary search? Why?",
            "Explain the concept of recursion and when it's appropriate to use.",
            "What are the SOLID principles? Give an example of each.",
            "Explain the difference between SQL and NoSQL databases.",
        ],
        "web_development": [
            "Explain the difference between REST and GraphQL. When would you use each?",
            "What happens when you type a URL in a browser and press Enter?",
            "How do you handle authentication and authorization in a web application?",
            "Explain CORS and why it exists.",
            "What are Web Workers and when would you use them?",
        ],
        "devops": [
            "Explain the concept of containerization and why Docker is popular.",
            "How would you set up a CI/CD pipeline for a web application?",
            "What is Kubernetes and when would you use it?",
            "Explain the difference between horizontal and vertical scaling.",
            "How do you handle secrets management in a cloud environment?",
        ],
    },
    "technical_data": {
        "machine_learning": [
            "Explain the difference between supervised and unsupervised learning.",
            "What is overfitting and how do you prevent it?",
            "Explain the bias-variance tradeoff.",
            "How would you handle imbalanced datasets?",
            "What is cross-validation and why is it important?",
        ],
        "data_engineering": [
            "Design an ETL pipeline for processing log data at scale.",
            "Explain the difference between batch and stream processing.",
            "How would you optimize a slow SQL query?",
            "What is data partitioning and when would you use it?",
            "Explain the concept of data lineage and why it matters.",
        ],
        "statistics": [
            "Explain the difference between correlation and causation.",
            "What is a p-value and how do you interpret it?",
            "When would you use A/B testing vs. multivariate testing?",
            "Explain the Central Limit Theorem.",
        ],
    },
    "product": {
        "product_sense": [
            "How would you improve [popular product]?",
            "Design a feature for helping users discover new content.",
            "How would you measure the success of a new feature?",
            "Walk me through how you would prioritize a product roadmap.",
        ],
        "metrics": [
            "What metrics would you track for a subscription-based product?",
            "How would you define and measure user engagement?",
            "Explain the difference between leading and lagging indicators.",
        ],
    },
}

# STAR method prompts
STAR_FRAMEWORK = {
    "S": "Situation: Describe the context. What was the background?",
    "T": "Task: What was your responsibility? What needed to be done?",
    "A": "Action: What specific steps did you take? Focus on YOUR actions.",
    "R": "Result: What was the outcome? Use metrics if possible.",
}


@dataclass
class InterviewQuestion:
    """An interview question with metadata."""
    question: str
    category: str
    subcategory: str
    difficulty: str  # easy, medium, hard
    tips: List[str] = field(default_factory=list)
    sample_answer_points: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "question": self.question,
            "category": self.category,
            "subcategory": self.subcategory,
            "difficulty": self.difficulty,
            "tips": self.tips,
            "sample_answer_points": self.sample_answer_points,
        }


@dataclass
class AnswerFeedback:
    """Feedback on an interview answer."""
    score: int  # 1-10
    strengths: List[str]
    improvements: List[str]
    star_analysis: Dict[str, str]
    revised_answer: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "strengths": self.strengths,
            "improvements": self.improvements,
            "star_analysis": self.star_analysis,
            "revised_answer": self.revised_answer,
        }


class InterviewCoach:
    """
    AI-powered interview preparation coach.
    
    Features:
    - Generate role-specific questions
    - Evaluate answers using STAR method
    - Provide personalized feedback
    - Suggest improvements
    """
    
    def __init__(self):
        self.ai_service = get_ai_service()
        self.question_bank = QUESTION_BANK
    
    def generate_questions(
        self,
        role: str,
        categories: List[str] = None,
        count: int = 5,
        difficulty: str = "medium",
    ) -> List[InterviewQuestion]:
        """
        Generate interview questions for a specific role.
        
        Args:
            role: Target job role
            categories: Question categories to include
            count: Number of questions to generate
            difficulty: Question difficulty level
        """
        logger.info(f"Generating {count} interview questions for {role}")
        
        questions = []
        
        # Determine relevant categories based on role
        if not categories:
            categories = self._get_role_categories(role)
        
        # Collect questions from categories
        for category in categories:
            if category in self.question_bank:
                for subcategory, q_list in self.question_bank[category].items():
                    for q in q_list:
                        questions.append(InterviewQuestion(
                            question=q,
                            category=category,
                            subcategory=subcategory,
                            difficulty=difficulty,
                            tips=self._get_question_tips(category, subcategory),
                            sample_answer_points=self._get_sample_points(category),
                        ))
        
        # Shuffle and limit
        random.shuffle(questions)
        return questions[:count]
    
    def generate_custom_question(
        self,
        role: str,
        skill: str,
        question_type: str = "technical",
    ) -> InterviewQuestion:
        """Generate a custom question using AI."""
        prompt = f"""Generate a {question_type} interview question for a {role} position 
        that tests knowledge of {skill}. 
        
        Format:
        Question: [The question]
        Tips: [2-3 tips for answering]
        Key points to cover: [3-4 points]
        """
        
        response = self.ai_service.generate(
            prompt=prompt,
            system_prompt="You are an experienced technical interviewer.",
            max_tokens=300,
        )
        
        # Parse response (simplified for mock)
        return InterviewQuestion(
            question=response.content.split('\n')[0].replace("Question:", "").strip(),
            category=question_type,
            subcategory=skill,
            difficulty="medium",
            tips=["Be specific with examples", "Explain your reasoning", "Ask clarifying questions if needed"],
            sample_answer_points=["Demonstrate understanding", "Show practical experience", "Discuss trade-offs"],
        )
    
    def evaluate_answer(
        self,
        question: str,
        answer: str,
        question_type: str = "behavioral",
    ) -> AnswerFeedback:
        """
        Evaluate an interview answer and provide feedback.
        
        Args:
            question: The interview question
            answer: Candidate's answer
            question_type: Type of question for evaluation criteria
        """
        logger.info("Evaluating interview answer")
        
        # For behavioral questions, analyze STAR format
        star_analysis = self._analyze_star(answer) if question_type == "behavioral" else {}
        
        # Calculate score based on various factors
        score = self._calculate_answer_score(answer, question_type, star_analysis)
        
        # Generate feedback
        strengths = self._identify_strengths(answer, question_type)
        improvements = self._identify_improvements(answer, question_type, star_analysis)
        
        # Generate improved answer using AI
        revised = self._generate_improved_answer(question, answer, question_type)
        
        return AnswerFeedback(
            score=score,
            strengths=strengths,
            improvements=improvements,
            star_analysis=star_analysis,
            revised_answer=revised,
        )
    
    def get_star_guidance(self) -> Dict[str, str]:
        """Get STAR method guidance."""
        return STAR_FRAMEWORK
    
    def _get_role_categories(self, role: str) -> List[str]:
        """Determine relevant question categories for a role."""
        role_lower = role.lower()
        
        categories = ["behavioral"]  # Always include behavioral
        
        if any(kw in role_lower for kw in ["software", "developer", "engineer", "swe"]):
            categories.append("technical_software")
        
        if any(kw in role_lower for kw in ["data", "ml", "machine learning", "analyst"]):
            categories.append("technical_data")
        
        if any(kw in role_lower for kw in ["product", "pm", "manager"]):
            categories.append("product")
        
        return categories
    
    def _get_question_tips(self, category: str, subcategory: str) -> List[str]:
        """Get tips for answering questions in a category."""
        tips = {
            "behavioral": [
                "Use the STAR method to structure your answer",
                "Be specific with examples from your experience",
                "Focus on YOUR actions and contributions",
                "Quantify results when possible",
            ],
            "technical_software": [
                "Think out loud as you work through the problem",
                "Ask clarifying questions before diving in",
                "Discuss trade-offs between different approaches",
                "Consider scalability and edge cases",
            ],
            "technical_data": [
                "Explain your reasoning step by step",
                "Mention relevant tools and technologies",
                "Discuss how you would validate your approach",
            ],
            "product": [
                "Start with understanding the user",
                "Define success metrics upfront",
                "Consider different user segments",
                "Think about technical feasibility",
            ],
        }
        
        return tips.get(category, ["Be clear and concise", "Provide specific examples"])
    
    def _get_sample_points(self, category: str) -> List[str]:
        """Get sample answer points for a category."""
        points = {
            "behavioral": [
                "Set the context clearly",
                "Explain the challenge or goal",
                "Describe your specific actions",
                "Share measurable results",
            ],
            "technical_software": [
                "Clarify requirements and constraints",
                "Start with a high-level design",
                "Dive into specific components",
                "Discuss trade-offs and alternatives",
            ],
        }
        
        return points.get(category, ["Provide relevant examples", "Be specific"])
    
    def _analyze_star(self, answer: str) -> Dict[str, str]:
        """Analyze answer for STAR method components."""
        analysis = {}
        answer_lower = answer.lower()
        
        # Simple heuristic analysis
        # Situation indicators
        if any(phrase in answer_lower for phrase in ["when i was", "at my previous", "in my role", "we were"]):
            analysis["situation"] = "Present - You set the context well"
        else:
            analysis["situation"] = "Missing - Add context about where/when this happened"
        
        # Task indicators
        if any(phrase in answer_lower for phrase in ["i was responsible", "my goal was", "needed to", "had to"]):
            analysis["task"] = "Present - Clear responsibility described"
        else:
            analysis["task"] = "Weak - Clarify what you specifically needed to accomplish"
        
        # Action indicators
        if any(phrase in answer_lower for phrase in ["i decided", "i implemented", "i created", "i led", "i built"]):
            analysis["action"] = "Strong - Good focus on your personal actions"
        elif "we" in answer_lower and "i" not in answer_lower:
            analysis["action"] = "Weak - Too much 'we', focus more on YOUR specific actions"
        else:
            analysis["action"] = "Present but could be stronger - Add more detail about what YOU did"
        
        # Result indicators
        if any(char in answer for char in ['%', '$']) or any(word in answer_lower for word in ["increased", "decreased", "improved", "reduced", "saved"]):
            analysis["result"] = "Strong - Good use of metrics and outcomes"
        else:
            analysis["result"] = "Weak - Add specific metrics or measurable outcomes"
        
        return analysis
    
    def _calculate_answer_score(
        self,
        answer: str,
        question_type: str,
        star_analysis: Dict[str, str],
    ) -> int:
        """Calculate answer quality score (1-10)."""
        score = 5  # Base score
        
        # Length check
        word_count = len(answer.split())
        if 100 <= word_count <= 300:
            score += 1
        elif word_count < 50:
            score -= 1
        
        # STAR analysis for behavioral
        if question_type == "behavioral":
            strong_count = sum(1 for v in star_analysis.values() if "Strong" in v or "Present" in v)
            score += min(strong_count, 2)
            
            weak_count = sum(1 for v in star_analysis.values() if "Weak" in v or "Missing" in v)
            score -= min(weak_count, 2)
        
        # Technical depth indicators
        if question_type in ["technical_software", "technical_data"]:
            technical_terms = ["algorithm", "complexity", "trade-off", "scalability", "performance", "design"]
            tech_count = sum(1 for term in technical_terms if term in answer.lower())
            score += min(tech_count, 2)
        
        return max(1, min(10, score))
    
    def _identify_strengths(self, answer: str, question_type: str) -> List[str]:
        """Identify strengths in the answer."""
        strengths = []
        answer_lower = answer.lower()
        
        # Check for specific examples
        if any(phrase in answer_lower for phrase in ["for example", "specifically", "in one case"]):
            strengths.append("Good use of specific examples")
        
        # Check for metrics
        if any(char in answer for char in ['%', '$']) or any(word in answer_lower for word in ["increased", "decreased", "improved"]):
            strengths.append("Strong quantification of results")
        
        # Check for first-person ownership
        if answer_lower.count("i ") > answer_lower.count("we "):
            strengths.append("Good focus on personal contributions")
        
        # Length appropriate
        if 100 <= len(answer.split()) <= 300:
            strengths.append("Answer length is appropriate")
        
        if not strengths:
            strengths.append("Attempt to answer the question")
        
        return strengths
    
    def _identify_improvements(
        self,
        answer: str,
        question_type: str,
        star_analysis: Dict[str, str],
    ) -> List[str]:
        """Identify areas for improvement."""
        improvements = []
        
        # STAR gaps
        for component, status in star_analysis.items():
            if "Weak" in status or "Missing" in status:
                improvements.append(f"Improve {component.upper()}: {status.split('-')[1].strip()}")
        
        # Length issues
        word_count = len(answer.split())
        if word_count < 50:
            improvements.append("Expand your answer with more details and examples")
        elif word_count > 400:
            improvements.append("Consider being more concise - focus on key points")
        
        # Metrics
        if '%' not in answer and '$' not in answer:
            improvements.append("Add specific metrics or numbers to quantify your impact")
        
        # Limit to top 3 improvements
        return improvements[:3]
    
    def _generate_improved_answer(
        self,
        question: str,
        original_answer: str,
        question_type: str,
    ) -> str:
        """Generate an improved version of the answer."""
        # For mock/development, provide template improvement
        if question_type == "behavioral":
            return f"""Here's a stronger version using STAR:

SITUATION: [Set the scene - when, where, what was the context]

TASK: [What was your specific responsibility or goal]

ACTION: [Describe the specific steps YOU took - use "I" not "we"]
- First, I analyzed the situation...
- Then, I developed a plan to...
- I implemented the solution by...

RESULT: [Quantify the outcome]
- Improved efficiency by X%
- Saved $Y in costs
- Reduced time by Z hours

Remember: Be specific, use numbers, and focus on YOUR contributions."""
        else:
            return f"""Here's a stronger approach:

1. Start by clarifying any assumptions
2. Outline your high-level approach
3. Dive into specific technical details
4. Discuss trade-offs and alternatives
5. Consider edge cases and scalability

Your original answer touched on good points. Expand on the technical depth and be more specific about implementation details."""


# Singleton instance
_coach_instance: Optional[InterviewCoach] = None


def get_interview_coach() -> InterviewCoach:
    """Get or create singleton InterviewCoach instance."""
    global _coach_instance
    if _coach_instance is None:
        _coach_instance = InterviewCoach()
    return _coach_instance
