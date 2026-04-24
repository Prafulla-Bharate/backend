"""
Adaptive Learning Engine
========================
Core engine for dynamic learning path updates based on user performance.

This engine:
1. Analyzes quiz performance to identify weak concepts
2. Generates remedial content via Gemini AI
3. Injects targeted resources into learning path
4. Tracks skill mastery with decay
5. Reviews project submissions
6. Verifies certificates
7. Sends refresher quizzes for skill retention

Architecture:
    User Performance → Analysis → Gemini AI → Path Update → Notification
"""

import logging
from datetime import timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from django.db import transaction
from django.db.models import Avg, F
from django.utils import timezone

from apps.learning.models import (
    LearningPath,
    LearningPhase,
    LearningResource,
    UserLearningPathEnrollment,
    UserResourceProgress,
    KnowledgeCheckpoint,
    UserCheckpointAttempt,
    # New adaptive models
    UserSkillMastery,
    PhaseInjection,
    ProjectSubmission,
    CertificateVerification,
    SkillRefresherQuiz,
    LearningPathUpdate,
)
from services.ai.gemini import get_gemini_service

logger = logging.getLogger(__name__)


class AdaptiveLearningEngine:
    """
    Main engine for adaptive learning path management.
    
    Responsibilities:
    - Analyze quiz results and identify weak areas
    - Generate remedial content using Gemini AI
    - Inject content into learning phases
    - Track and update skill mastery
    - Handle project reviews
    - Manage certificate verification
    - Orchestrate skill refresher system
    """
    
    # Configuration
    WEAK_SCORE_THRESHOLD = 70  # Below this, trigger remedial content
    STRONG_SCORE_THRESHOLD = 90  # Above this, offer advanced content
    SKILL_DECAY_DAYS = 30  # Start decay check after this many days
    REFRESHER_QUIZ_QUESTIONS = 5  # Questions in refresher quiz
    
    def __init__(self):
        self.gemini = get_gemini_service()
    
    # =========================================================================
    # QUIZ PERFORMANCE ANALYSIS
    # =========================================================================
    
    def analyze_quiz_performance(
        self,
        attempt: UserCheckpointAttempt
    ) -> Dict[str, Any]:
        """
        Analyze a quiz attempt to identify weak concepts.
        
        Returns:
            {
                "score": 65,
                "passed": False,
                "weak_concepts": ["List Comprehensions", "Lambda Functions"],
                "strong_concepts": ["Variables", "Loops"],
                "recommendation": "remedial" | "continue" | "advanced",
                "detailed_analysis": {...}
            }
        """
        checkpoint = attempt.checkpoint
        questions = checkpoint.questions
        answers = attempt.answers
        feedback = attempt.feedback
        
        weak_concepts = []
        strong_concepts = []
        concept_scores = {}
        
        for q in questions:
            q_id = str(q.get("id", ""))
            topic = q.get("topic", q.get("concept", "General"))
            is_correct = feedback.get(q_id, {}).get("is_correct", False)
            
            if topic not in concept_scores:
                concept_scores[topic] = {"correct": 0, "total": 0}
            
            concept_scores[topic]["total"] += 1
            if is_correct:
                concept_scores[topic]["correct"] += 1
        
        # Classify concepts
        for concept, scores in concept_scores.items():
            percentage = (scores["correct"] / scores["total"]) * 100 if scores["total"] > 0 else 0
            if percentage < 50:
                weak_concepts.append(concept)
            elif percentage >= 80:
                strong_concepts.append(concept)
        
        # Determine recommendation
        if attempt.score < self.WEAK_SCORE_THRESHOLD:
            recommendation = "remedial"
        elif attempt.score >= self.STRONG_SCORE_THRESHOLD:
            recommendation = "advanced"
        else:
            recommendation = "continue"
        
        return {
            "score": attempt.score,
            "passed": attempt.passed,
            "weak_concepts": weak_concepts,
            "strong_concepts": strong_concepts,
            "concept_scores": concept_scores,
            "recommendation": recommendation,
            "detailed_analysis": {
                "total_questions": len(questions),
                "correct_answers": sum(1 for q_id, f in feedback.items() if f.get("is_correct")),
                "time_taken_seconds": attempt.time_taken_seconds,
                "attempt_number": attempt.attempt_number
            }
        }
    
    # =========================================================================
    # REMEDIAL CONTENT GENERATION
    # =========================================================================
    
    @transaction.atomic
    def generate_remedial_content(
        self,
        enrollment: UserLearningPathEnrollment,
        phase: LearningPhase,
        weak_concepts: List[str],
        quiz_score: int
    ) -> Optional[PhaseInjection]:
        """
        Generate remedial content for weak concepts using Gemini AI.
        Creates a PhaseInjection with targeted resources.
        """
        if not weak_concepts:
            return None
        
        # Build prompt for Gemini
        prompt = f"""A user is learning "{phase.learning_path.title}" and just completed the phase "{phase.title}".
They scored {quiz_score}% on the quiz and struggled with these concepts:
{', '.join(weak_concepts)}

The phase covers these skills: {', '.join(phase.skills_covered) if phase.skills_covered else 'General skills'}

Generate remedial learning content to help them master these weak areas.

## REQUIREMENTS
1. Provide 2-4 targeted resources (videos, articles, tutorials)
2. Each resource should focus on ONE weak concept
3. Include free resources from YouTube, freeCodeCamp, MDN, W3Schools
4. Add a short verification quiz (3 questions) to check understanding

## RESPONSE FORMAT (JSON only)
{{
  "title": "Mastering [weak concepts]",
  "description": "Brief description of what user will learn",
  "resources": [
    {{
      "title": "Resource title",
      "url": "https://...",
      "type": "video|article|tutorial",
      "platform": "YouTube|freeCodeCamp|MDN|Other",
      "duration_minutes": 15,
      "concept_covered": "The specific weak concept this addresses",
      "why_helpful": "Brief explanation of why this helps"
    }}
  ],
  "verification_quiz": {{
    "passing_score": 70,
    "questions": [
      {{
        "id": "q1",
        "question": "Question text",
        "concept": "Which weak concept this tests",
        "options": [
          {{"id": "a", "text": "Option A"}},
          {{"id": "b", "text": "Option B"}},
          {{"id": "c", "text": "Option C"}},
          {{"id": "d", "text": "Option D"}}
        ],
        "correct_answer": "b",
        "explanation": "Why this is correct"
      }}
    ]
  }},
  "estimated_hours": 2
}}"""

        try:
            result = self.gemini.generate_json(
                prompt=prompt,
                system_prompt="You are an expert learning curriculum designer. Create targeted remedial content to help students master concepts they're struggling with. Always provide real, working URLs to free learning resources.",
                temperature=0.6,
                max_tokens=2000
            )
            
            if not result or "error" in result:
                logger.warning(f"Gemini failed to generate remedial content: {result}")
                return self._create_fallback_injection(enrollment, phase, weak_concepts)
            
            # Create the injection
            injection = PhaseInjection.objects.create(
                enrollment=enrollment,
                target_phase=phase,
                injection_type=PhaseInjection.InjectionType.REMEDIAL,
                title=result.get("title", f"Review: {', '.join(weak_concepts[:2])}"),
                reason=f"Quiz score was {quiz_score}%. Struggled with: {', '.join(weak_concepts)}",
                weak_concepts=weak_concepts,
                injected_resources=result.get("resources", []),
                verification_quiz=result.get("verification_quiz", {}),
                priority=2  # High priority for remedial
            )
            
            # Log the path update
            LearningPathUpdate.objects.create(
                enrollment=enrollment,
                update_type=LearningPathUpdate.UpdateType.INJECTION_ADDED,
                description=f"Added remedial content for: {', '.join(weak_concepts)}",
                trigger_source="quiz_performance",
                trigger_data={
                    "quiz_score": quiz_score,
                    "weak_concepts": weak_concepts,
                    "phase_id": str(phase.id)
                },
                changes={"added": [str(injection.id)]},
                ai_reasoning=result.get("description", "")
            )
            
            logger.info(f"Created remedial injection {injection.id} for user {enrollment.user.id}")
            return injection
            
        except Exception as e:
            logger.error(f"Error generating remedial content: {e}")
            return self._create_fallback_injection(enrollment, phase, weak_concepts)
    
    def _create_fallback_injection(
        self,
        enrollment: UserLearningPathEnrollment,
        phase: LearningPhase,
        weak_concepts: List[str]
    ) -> PhaseInjection:
        """Create a basic injection when Gemini fails."""
        return PhaseInjection.objects.create(
            enrollment=enrollment,
            target_phase=phase,
            injection_type=PhaseInjection.InjectionType.REMEDIAL,
            title=f"Review: {', '.join(weak_concepts[:2])}",
            reason="Additional practice recommended based on quiz performance",
            weak_concepts=weak_concepts,
            injected_resources=[
                {
                    "title": f"Review {concept}",
                    "url": f"https://www.google.com/search?q={concept.replace(' ', '+')}+tutorial",
                    "type": "article",
                    "platform": "Web Search",
                    "duration_minutes": 20,
                    "concept_covered": concept
                }
                for concept in weak_concepts[:3]
            ],
            verification_quiz={},
            priority=1
        )
    
    # =========================================================================
    # ADVANCED CONTENT FOR HIGH PERFORMERS
    # =========================================================================
    
    @transaction.atomic
    def generate_advanced_content(
        self,
        enrollment: UserLearningPathEnrollment,
        phase: LearningPhase,
        quiz_score: int
    ) -> Optional[PhaseInjection]:
        """Generate advanced/bonus content for high performers."""
        
        prompt = f"""A user excelled in "{phase.title}" with a {quiz_score}% score!
They've mastered the basics and are ready for advanced challenges.

Phase skills: {', '.join(phase.skills_covered) if phase.skills_covered else 'General skills'}

Generate advanced content to challenge them further.

## RESPONSE FORMAT (JSON only)
{{
  "title": "Advanced: [topic]",
  "description": "What advanced concepts they'll learn",
  "resources": [
    {{
      "title": "Advanced resource title",
      "url": "https://...",
      "type": "video|article|project",
      "platform": "YouTube|GitHub|Medium",
      "duration_minutes": 30,
      "skill_level": "advanced",
      "what_youll_learn": "Brief description"
    }}
  ],
  "challenge_project": {{
    "title": "Project title",
    "description": "What to build",
    "requirements": ["req1", "req2"],
    "skills_practiced": ["skill1", "skill2"]
  }},
  "estimated_hours": 3
}}"""

        try:
            result = self.gemini.generate_json(
                prompt=prompt,
                system_prompt="You are an expert curriculum designer. Create challenging advanced content for high-performing students.",
                temperature=0.7,
                max_tokens=1500
            )
            
            if not result or "error" in result:
                return None
            
            injection = PhaseInjection.objects.create(
                enrollment=enrollment,
                target_phase=phase,
                injection_type=PhaseInjection.InjectionType.ADVANCED,
                title=result.get("title", "Advanced Challenge"),
                reason=f"Excellent performance ({quiz_score}%)! Advanced content unlocked.",
                weak_concepts=[],  # No weak concepts for advanced
                injected_resources=result.get("resources", []),
                verification_quiz={},
                priority=0  # Lower priority - optional
            )
            
            LearningPathUpdate.objects.create(
                enrollment=enrollment,
                update_type=LearningPathUpdate.UpdateType.ADVANCED_CONTENT,
                description=f"Unlocked advanced content for phase: {phase.title}",
                trigger_source="high_quiz_score",
                trigger_data={"quiz_score": quiz_score, "phase_id": str(phase.id)},
                changes={"added": [str(injection.id)]}
            )
            
            return injection
            
        except Exception as e:
            logger.error(f"Error generating advanced content: {e}")
            return None
    
    # =========================================================================
    # MAIN ADAPTATION HANDLER
    # =========================================================================
    
    def handle_quiz_completion(
        self,
        attempt: UserCheckpointAttempt
    ) -> Dict[str, Any]:
        """
        Main handler called after a user completes a quiz.
        Analyzes performance and triggers appropriate adaptations.
        
        Returns summary of actions taken.
        """
        enrollment = attempt.enrollment
        phase = attempt.checkpoint.phase
        
        if not enrollment or not phase:
            return {"status": "skipped", "reason": "No enrollment or phase"}
        
        # Analyze the attempt
        analysis = self.analyze_quiz_performance(attempt)
        
        actions_taken = []
        
        # Update skill mastery for concepts tested
        self._update_skill_mastery_from_quiz(
            user=attempt.user,
            phase=phase,
            analysis=analysis
        )
        actions_taken.append("skill_mastery_updated")
        
        # Take action based on performance
        if analysis["recommendation"] == "remedial" and analysis["weak_concepts"]:
            injection = self.generate_remedial_content(
                enrollment=enrollment,
                phase=phase,
                weak_concepts=analysis["weak_concepts"],
                quiz_score=attempt.score
            )
            if injection:
                actions_taken.append(f"remedial_content_added:{injection.id}")
        
        elif analysis["recommendation"] == "advanced":
            injection = self.generate_advanced_content(
                enrollment=enrollment,
                phase=phase,
                quiz_score=attempt.score
            )
            if injection:
                actions_taken.append(f"advanced_content_unlocked:{injection.id}")
        
        return {
            "status": "processed",
            "analysis": analysis,
            "actions_taken": actions_taken,
            "recommendation": analysis["recommendation"]
        }
    
    def _update_skill_mastery_from_quiz(
        self,
        user,
        phase: LearningPhase,
        analysis: Dict[str, Any]
    ):
        """Update user's skill mastery based on quiz performance."""
        skills_covered = phase.skills_covered or []
        
        for skill in skills_covered:
            mastery, created = UserSkillMastery.objects.get_or_create(
                user=user,
                skill_name=skill,
                defaults={"mastery_score": 0}
            )
            
            # Determine score contribution for this skill
            if skill.lower() in [c.lower() for c in analysis.get("strong_concepts", [])]:
                score_delta = min(15, 100 - mastery.mastery_score)  # Cap at 100
            elif skill.lower() in [c.lower() for c in analysis.get("weak_concepts", [])]:
                score_delta = 5  # Minimal improvement for weak areas
            else:
                score_delta = 10  # Average improvement
            
            # Update mastery
            mastery.mastery_score = min(100, mastery.mastery_score + score_delta)
            mastery.record_verification(
                verification_type="quiz",
                score=analysis["score"],
                source=f"Phase: {phase.title}"
            )
            mastery.learned_from.append({
                "phase_id": str(phase.id),
                "phase_title": phase.title,
                "quiz_score": analysis["score"]
            })
            mastery.save()
    
    # =========================================================================
    # PROJECT SUBMISSION REVIEW
    # =========================================================================

    @staticmethod
    def _analyze_phase_alignment(submission: ProjectSubmission) -> Dict[str, Any]:
        """Simple overlap-based check for project relevance to selected phase."""
        phase = submission.phase
        if not phase:
            return {
                "has_phase": False,
                "phase_title": None,
                "phase_skills": [],
                "matched_phase_skills": [],
                "is_phase_related": True,
                "alignment_reason": "No phase selected; reviewed as standalone project.",
            }

        phase_skills = [
            str(skill).strip()
            for skill in (phase.skills_covered or [])
            if str(skill).strip()
        ]

        project_text = " ".join([
            submission.title or "",
            submission.description or "",
            " ".join(submission.technologies or []),
            " ".join(submission.skills_demonstrated or []),
        ]).lower()

        matched_phase_skills = [
            skill for skill in phase_skills
            if skill.lower() in project_text
        ]

        phase_title_tokens = [
            token.lower()
            for token in str(phase.title or "").split()
            if len(token) > 3
        ]
        title_overlap = any(token in project_text for token in phase_title_tokens)

        is_phase_related = bool(matched_phase_skills or title_overlap)
        alignment_reason = (
            "Project appears aligned with selected phase context."
            if is_phase_related
            else "Project appears outside selected phase; do not require unrelated phase skills."
        )

        return {
            "has_phase": True,
            "phase_title": phase.title,
            "phase_skills": phase_skills,
            "matched_phase_skills": matched_phase_skills,
            "is_phase_related": is_phase_related,
            "alignment_reason": alignment_reason,
        }
    
    @transaction.atomic
    def review_project_submission(
        self,
        submission: ProjectSubmission
    ) -> ProjectSubmission:
        """
        Review a project submission using Gemini AI.
        Updates submission with scores and feedback.
        """
        submission.status = ProjectSubmission.SubmissionStatus.UNDER_REVIEW
        submission.save()

        phase_alignment = self._analyze_phase_alignment(submission)

        if phase_alignment["has_phase"]:
            phase_context = f"""## PHASE CONTEXT
- **Current Phase**: {phase_alignment['phase_title']}
- **Phase Skills**: {', '.join(phase_alignment['phase_skills']) if phase_alignment['phase_skills'] else 'Not defined'}
- **Matched Project-Phase Skills**: {', '.join(phase_alignment['matched_phase_skills']) if phase_alignment['matched_phase_skills'] else 'None'}
- **Phase Related**: {'Yes' if phase_alignment['is_phase_related'] else 'No'}
"""
            alignment_rule = (
                "Project is phase-related. Mention only clearly matched phase skills; do not invent additional phase requirements."
                if phase_alignment["is_phase_related"]
                else "Project is NOT phase-related. Do not require or penalize missing phase skills; review only submitted scope."
            )
        else:
            phase_context = "## PHASE CONTEXT\n- Standalone project submission"
            alignment_rule = "No phase-specific expectations apply."
        
        prompt = f"""Review this coding project submission:

## PROJECT DETAILS
- **Title**: {submission.title}
- **Description**: {submission.description}
- **GitHub URL**: {submission.project_url}
- **Technologies**: {', '.join(submission.technologies) if submission.technologies else 'Not specified'}
- **Skills Demonstrated**: {', '.join(submission.skills_demonstrated) if submission.skills_demonstrated else 'Not specified'}

{phase_context}

## ALIGNMENT RULE
{alignment_rule}

## REVIEW CRITERIA
1. **Code Quality** (0-100): Clean code, proper naming, comments
2. **Documentation** (0-100): README, code comments, setup instructions
3. **Functionality** (0-100): Does it work as described?
4. **Best Practices** (0-100): Design patterns, error handling, testing

Note: You cannot actually access the GitHub URL, so base your review on the description and technologies listed. Provide constructive feedback.

## RESPONSE FORMAT (JSON only)
{{
  "overall_score": 85,
  "code_quality": {{
    "score": 80,
    "feedback": "Specific feedback about code quality"
  }},
  "documentation": {{
    "score": 90,
    "feedback": "Specific feedback about documentation"
  }},
  "functionality": {{
    "score": 85,
    "feedback": "Feedback about functionality"
  }},
  "best_practices": {{
    "score": 80,
    "feedback": "Feedback about best practices"
  }},
  "strengths": ["strength1", "strength2", "strength3"],
  "improvements": ["improvement1", "improvement2", "improvement3"],
  "detailed_feedback": "2-3 paragraph comprehensive feedback",
  "recommendation": "approved|needs_revision|rejected",
    "phase_alignment": {{
        "status": "aligned|not_aligned|standalone",
        "note": "One short sentence about current phase relevance"
    }},
  "next_steps": ["What the user should do next"]
}}"""

        try:
            result = self.gemini.generate_json(
                prompt=prompt,
                system_prompt="You are a senior software engineer reviewing project submissions. Be constructive, specific, and encouraging while maintaining high standards.",
                temperature=0.5,
                max_tokens=2000
            )
            
            if result and "error" not in result:
                if "phase_alignment" not in result or not isinstance(result.get("phase_alignment"), dict):
                    result["phase_alignment"] = {}

                result["phase_alignment"].update({
                    "status": (
                        "standalone"
                        if not phase_alignment["has_phase"]
                        else ("aligned" if phase_alignment["is_phase_related"] else "not_aligned")
                    ),
                    "current_phase": phase_alignment["phase_title"],
                    "matched_phase_skills": phase_alignment["matched_phase_skills"],
                    "note": phase_alignment["alignment_reason"],
                })

                submission.ai_review = result
                submission.overall_score = result.get("overall_score", 0)
                
                # Map recommendation to status
                rec = result.get("recommendation", "needs_revision")
                if rec == "approved":
                    submission.status = ProjectSubmission.SubmissionStatus.APPROVED
                elif rec == "rejected":
                    submission.status = ProjectSubmission.SubmissionStatus.REJECTED
                else:
                    submission.status = ProjectSubmission.SubmissionStatus.NEEDS_REVISION
                
                submission.reviewed_at = timezone.now()
                
                # Update skill mastery if approved
                if submission.status == ProjectSubmission.SubmissionStatus.APPROVED:
                    self._update_skill_mastery_from_project(submission)
                
            else:
                submission.status = ProjectSubmission.SubmissionStatus.REVIEWED
                submission.ai_review = {"error": "AI review failed", "manual_review_required": True}
                submission.reviewed_at = timezone.now()
            
        except Exception as e:
            logger.error(f"Project review failed: {e}")
            submission.status = ProjectSubmission.SubmissionStatus.REVIEWED
            submission.ai_review = {"error": str(e)}
            submission.reviewed_at = timezone.now()
        
        submission.save()
        
        # Log path update if part of enrollment
        if submission.enrollment:
            LearningPathUpdate.objects.create(
                enrollment=submission.enrollment,
                update_type=LearningPathUpdate.UpdateType.INJECTION_ADDED,
                description=f"Project reviewed: {submission.title}",
                trigger_source="project_submission",
                trigger_data={
                    "project_id": str(submission.id),
                    "score": submission.overall_score,
                    "status": submission.status
                }
            )
        
        return submission
    
    def _update_skill_mastery_from_project(self, submission: ProjectSubmission):
        """Update skill mastery based on approved project."""
        skills = submission.skills_demonstrated or []
        
        for skill in skills:
            mastery, _ = UserSkillMastery.objects.get_or_create(
                user=submission.user,
                skill_name=skill,
                defaults={"mastery_score": 0}
            )
            
            # Projects give significant mastery boost
            mastery.mastery_score = min(100, mastery.mastery_score + 20)
            mastery.record_verification(
                verification_type="project",
                score=submission.overall_score or 80,
                source=submission.title
            )
            mastery.save()
    
    # =========================================================================
    # CERTIFICATE VERIFICATION
    # =========================================================================
    
    @transaction.atomic
    def verify_certificate(
        self,
        verification: CertificateVerification
    ) -> CertificateVerification:
        """
        Verify a certificate submission.
        Uses URL checking and AI for validation.
        """
        # Try URL verification first (for platforms with verifiable URLs)
        if verification.certificate_url:
            url_result = self._verify_certificate_url(verification)
            if url_result["verified"]:
                verification.status = CertificateVerification.VerificationStatus.VERIFIED
                verification.verification_method = CertificateVerification.VerificationMethod.URL_CHECK
                verification.confidence_score = url_result["confidence"]
                verification.verified_at = timezone.now()
                verification.save()
                
                # Update skill mastery
                self._update_skill_mastery_from_certificate(verification)
                return verification
        
        # Fall back to AI-based verification
        verification.status = CertificateVerification.VerificationStatus.MANUAL_REVIEW
        verification.verification_method = CertificateVerification.VerificationMethod.MANUAL
        verification.verification_notes = "Automatic verification not available. Manual review required."
        verification.save()
        
        return verification
    
    def _verify_certificate_url(self, verification: CertificateVerification) -> Dict[str, Any]:
        """Verify certificate via URL patterns."""
        url = verification.certificate_url.lower()
        
        # Known verification URL patterns
        verified_patterns = [
            ("coursera.org/verify", 0.95),
            ("coursera.org/account/accomplishments", 0.95),
            ("udemy.com/certificate", 0.90),
            ("credential.linkedin.com", 0.95),
            ("credly.com/badges", 0.95),
            ("freecodecamp.org/certification", 0.95),
            ("credential.net", 0.90),
        ]
        
        for pattern, confidence in verified_patterns:
            if pattern in url:
                return {"verified": True, "confidence": confidence}
        
        return {"verified": False, "confidence": 0}
    
    def _update_skill_mastery_from_certificate(self, verification: CertificateVerification):
        """Update skill mastery from verified certificate."""
        skills = verification.skills_covered or []
        
        for skill in skills:
            mastery, _ = UserSkillMastery.objects.get_or_create(
                user=verification.user,
                skill_name=skill,
                defaults={"mastery_score": 0}
            )
            
            # Certificates give strong mastery boost
            mastery.mastery_score = min(100, mastery.mastery_score + 25)
            mastery.record_verification(
                verification_type="certificate",
                score=95,  # Certificates are strong verification
                source=f"{verification.platform}: {verification.course_name}"
            )
            mastery.save()
        
        # Auto-complete resource if linked
        if verification.resource and verification.enrollment:
            UserResourceProgress.objects.update_or_create(
                user=verification.user,
                resource=verification.resource,
                defaults={
                    "status": UserResourceProgress.ProgressStatus.COMPLETED,
                    "progress_percentage": 100,
                    "completed_at": timezone.now()
                }
            )
    
    # =========================================================================
    # SKILL DECAY & REFRESHER SYSTEM
    # =========================================================================
    
    def check_skill_decay(self, user) -> List[UserSkillMastery]:
        """
        Check for skills that may have decayed due to inactivity.
        Returns list of skills needing refresher.

        NOTE: This is a pure READ operation — it does NOT mutate or save any
        mastery records.  Actual decay application happens only inside the
        Celery task `run_skill_decay_check` to avoid side-effects on GET
        requests.
        """
        cutoff_date = timezone.now() - timedelta(days=self.SKILL_DECAY_DAYS)

        decaying_skills = UserSkillMastery.objects.filter(
            user=user,
            last_verified_at__lt=cutoff_date,
            mastery_score__gt=20,  # Only check skills worth refreshing
        )

        skills_needing_refresh = []

        for mastery in decaying_skills:
            days_inactive = (
                (timezone.now() - mastery.last_verified_at).days
                if mastery.last_verified_at
                else 90
            )

            # Compute what the decayed score *would* be (do NOT save)
            decay_factor = max(0.5, 1.0 - (days_inactive * 0.005))
            projected_score = mastery.mastery_score * decay_factor

            # If projected score drops significantly, flag for refresh
            if projected_score < 60 and mastery.mastery_level not in [
                UserSkillMastery.MasteryLevel.NOVICE,
                UserSkillMastery.MasteryLevel.BEGINNER,
            ]:
                skills_needing_refresh.append(mastery)

        return skills_needing_refresh
    
    @transaction.atomic
    def generate_refresher_quiz(
        self,
        user,
        skill_mastery: UserSkillMastery
    ) -> SkillRefresherQuiz:
        """Generate a refresher quiz to maintain skill mastery."""
        
        prompt = f"""Generate a quick refresher quiz for the skill: {skill_mastery.skill_name}

The user previously had {skill_mastery.mastery_score}% mastery but hasn't practiced in a while.

Create {self.REFRESHER_QUIZ_QUESTIONS} multiple-choice questions to test if they still remember key concepts.

## RESPONSE FORMAT (JSON only)
{{
  "questions": [
    {{
      "id": "q1",
      "question": "Question text",
      "options": [
        {{"id": "a", "text": "Option A"}},
        {{"id": "b", "text": "Option B"}},
        {{"id": "c", "text": "Option C"}},
        {{"id": "d", "text": "Option D"}}
      ],
      "correct_answer": "b",
      "explanation": "Brief explanation"
    }}
  ]
}}"""

        try:
            result = self.gemini.generate_json(
                prompt=prompt,
                system_prompt="Generate clear, concise quiz questions to test skill retention.",
                temperature=0.5,
                max_tokens=1500
            )
            
            questions = result.get("questions", []) if result else []
            
        except Exception as e:
            logger.error(f"Failed to generate refresher quiz: {e}")
            questions = []
        
        quiz = SkillRefresherQuiz.objects.create(
            user=user,
            skill_mastery=skill_mastery,
            skill_name=skill_mastery.skill_name,
            questions=questions,
            status=SkillRefresherQuiz.QuizStatus.PENDING,
            expires_at=timezone.now() + timedelta(days=7),
            mastery_before=skill_mastery.mastery_score
        )
        
        return quiz
    
    def process_refresher_quiz_result(
        self,
        quiz: SkillRefresherQuiz,
        answers: Dict[str, str]
    ) -> SkillRefresherQuiz:
        """Process refresher quiz answers and update skill mastery."""
        quiz.answers = answers
        quiz.completed_at = timezone.now()
        
        # Grade the quiz
        correct = 0
        total = len(quiz.questions)
        
        for q in quiz.questions:
            q_id = q.get("id", "")
            if answers.get(q_id) == q.get("correct_answer"):
                correct += 1
        
        quiz.score = int((correct / total) * 100) if total > 0 else 0
        quiz.passed = quiz.score >= 70
        quiz.status = SkillRefresherQuiz.QuizStatus.COMPLETED
        
        # Update skill mastery
        mastery = quiz.skill_mastery
        mastery.record_verification(
            verification_type="refresher",
            score=quiz.score,
            source="Skill Refresher Quiz"
        )
        mastery.save()
        
        quiz.mastery_after = mastery.mastery_score
        quiz.save()
        
        return quiz
    
    # =========================================================================
    # PATH UPDATE HELPERS
    # =========================================================================
    
    def get_pending_injections(
        self,
        enrollment: UserLearningPathEnrollment
    ) -> List[PhaseInjection]:
        """Get all pending injections for an enrollment."""
        return PhaseInjection.objects.filter(
            enrollment=enrollment,
            is_completed=False
        ).order_by("-priority", "created_at")
    
    def complete_injection(
        self,
        injection: PhaseInjection,
        quiz_score: Optional[int] = None
    ):
        """Mark an injection as completed."""
        injection.is_completed = True
        injection.completed_at = timezone.now()
        if quiz_score is not None:
            injection.completion_score = quiz_score
        injection.save()
    
    def get_learning_path_summary(
        self,
        enrollment: UserLearningPathEnrollment
    ) -> Dict[str, Any]:
        """Get comprehensive summary of user's learning path status."""
        
        # Get all path updates
        updates = LearningPathUpdate.objects.filter(
            enrollment=enrollment
        ).order_by("-created_at")[:10]
        
        # Get pending injections
        pending_injections = self.get_pending_injections(enrollment)
        
        # Get skill masteries for skills in this path
        path_skills = enrollment.learning_path.skills_covered or []
        skill_masteries = UserSkillMastery.objects.filter(
            user=enrollment.user,
            skill_name__in=path_skills
        )
        
        # Get project submissions
        projects = ProjectSubmission.objects.filter(
            enrollment=enrollment
        )
        
        # Get certificates
        certificates = CertificateVerification.objects.filter(
            enrollment=enrollment
        )
        
        return {
            "enrollment_id": str(enrollment.id),
            "path_title": enrollment.learning_path.title,
            "overall_progress": enrollment.progress_percentage,
            "status": enrollment.status,
            "phases_completed": len(enrollment.completed_phases),
            "total_phases": enrollment.learning_path.phases.count(),
            "pending_injections": [
                {
                    "id": str(inj.id),
                    "type": inj.injection_type,
                    "title": inj.title,
                    "reason": inj.reason
                }
                for inj in pending_injections
            ],
            "skill_masteries": [
                {
                    "skill": m.skill_name,
                    "mastery": m.mastery_score,
                    "level": m.mastery_level
                }
                for m in skill_masteries
            ],
            "projects_submitted": projects.count(),
            "projects_approved": projects.filter(
                status=ProjectSubmission.SubmissionStatus.APPROVED
            ).count(),
            "certificates_verified": certificates.filter(
                status=CertificateVerification.VerificationStatus.VERIFIED
            ).count(),
            "recent_updates": [
                {
                    "type": u.update_type,
                    "description": u.description,
                    "date": u.created_at.isoformat()
                }
                for u in updates[:5]
            ],
            "adaptive_features": {
                "remedial_content_added": pending_injections.filter(
                    injection_type=PhaseInjection.InjectionType.REMEDIAL
                ).count(),
                "advanced_content_unlocked": pending_injections.filter(
                    injection_type=PhaseInjection.InjectionType.ADVANCED
                ).count()
            }
        }


# Singleton instance
_adaptive_engine: Optional[AdaptiveLearningEngine] = None


def get_adaptive_learning_engine() -> AdaptiveLearningEngine:
    """Get or create the AdaptiveLearningEngine instance."""
    global _adaptive_engine
    if _adaptive_engine is None:
        _adaptive_engine = AdaptiveLearningEngine()
    return _adaptive_engine
