"""
Interview Views
===============
API views for interview-related endpoints.
"""

import logging

from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.interview.models import (
    InterviewQuestion,
    InterviewSession,
    InterviewResponse,
)
from apps.interview.serializers import (
    InterviewSessionSerializer,
    InterviewSessionListSerializer,
    CreateSessionSerializer,
    InterviewResponseSerializer,
    SubmitResponseSerializer,
    InterviewTipSerializer,
    InterviewScheduleListSerializer,
    PracticeStatsSerializer,
)
from apps.interview.services import (
    SessionService,
    ResponseService,
    ScheduleService,
    TipService,
    StatsService,
    HostedInterviewAIService,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Session Views
# ============================================================================

class SessionViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    """List/create interview sessions with actions used by frontend."""
    
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post"]
    ordering = "-created_at"
    
    def get_queryset(self):
        """Return sessions for current user."""
        status_filter = self.request.query_params.get("status")
        session_type = self.request.query_params.get("type")
        
        return SessionService.get_user_sessions(
            self.request.user,
            status=status_filter,
            session_type=session_type
        )
    
    def get_serializer_class(self):
        """Return appropriate serializer."""
        if self.action == "list":
            return InterviewSessionListSerializer
        if self.action == "create":
            return CreateSessionSerializer
        return InterviewSessionSerializer
    
    def create(self, request, *args, **kwargs):
        """Create a new session."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        
        # Get related objects
        job_application = None
        if "job_application_id" in data:
            from apps.jobs.models import JobApplication
            try:
                job_application = JobApplication.objects.get(
                    id=data["job_application_id"],
                    user=request.user
                )
            except JobApplication.DoesNotExist:
                pass
        
        target_career = None
        if "target_career_id" in data:
            from apps.career.models import CareerPath
            try:
                target_career = CareerPath.objects.get(
                    id=data["target_career_id"]
                )
            except CareerPath.DoesNotExist:
                pass
        
        session = SessionService.create_session(
            user=request.user,
            title=data["title"],
            session_type=data.get("session_type", InterviewSession.SessionType.PRACTICE),
            job_application=job_application,
            target_career=target_career,
            target_company=data.get("target_company", ""),
            question_types=data.get("question_types"),
            difficulty_preference=data.get("difficulty_preference", InterviewQuestion.DifficultyLevel.MEDIUM),
            num_questions=data.get("num_questions", 5),
            duration_minutes=data.get("duration_minutes", 30),
            technical_mcq_count=data.get("technical_mcq_count"),
            coding_count=data.get("coding_count"),
            coding_language=data.get("coding_language", "python"),
            coding_mode=data.get("coding_mode", "function"),
            real_section=data.get("real_section", ""),
            scheduled_at=data.get("scheduled_at")
        )
        
        return Response(
            InterviewSessionSerializer(session).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        """Start a session."""
        session = self.get_object()
        
        try:
            session = SessionService.start_session(session)
            return Response(InterviewSessionSerializer(session).data)
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        """Complete a session."""
        session = self.get_object()
        session = SessionService.complete_session(session)
        return Response(InterviewSessionSerializer(session).data)
    
    @action(detail=True, methods=["get"])
    def next_question(self, request, pk=None):
        """Get next unanswered question."""
        session = self.get_object()
        response = session.responses.filter(
            completed_at__isnull=True
        ).order_by("order").first()
        
        if not response:
            return Response(
                {"detail": "All questions answered."},
                status=status.HTTP_200_OK
            )
        
        return Response(InterviewResponseSerializer(response).data)


# ============================================================================
# Response Views
# ============================================================================

class ResponseView(APIView):
    """Submit a specific response."""
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request, response_id):
        """Submit a response."""
        try:
            response = InterviewResponse.objects.get(
                id=response_id,
                session__user=request.user
            )
        except InterviewResponse.DoesNotExist:
            return Response(
                {"detail": "Response not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = SubmitResponseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Mark start time if not set
        if not response.started_at:
            response.started_at = timezone.now()

        try:
            response = ResponseService.submit_response(
                response,
                **serializer.validated_data
            )
        except ValueError as submit_err:
            logger.warning(f"Response submit validation failed for {response_id}: {submit_err}")
            return Response(
                {"detail": str(submit_err)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as submit_err:
            logger.warning(f"Response submission failed for {response_id}: {submit_err}", exc_info=True)
            return Response(
                {"detail": "Could not process this response. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Evaluate synchronously so the caller gets immediate AI feedback.
        # evaluate_response_with_ai has a guaranteed fallback â€” it never raises.
        try:
            response = ResponseService.evaluate_response_with_ai(response)
        except ValueError as _eval_value_err:
            return Response(
                {"detail": str(_eval_value_err)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as _eval_err:
            logger.warning(f"Inline evaluation failed for response {response_id}: {_eval_err}")

        return Response(InterviewResponseSerializer(response).data)


class UpcomingSchedulesView(APIView):
    """Get upcoming interview schedules for current user."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        days = int(request.query_params.get("days", 7))
        schedules = ScheduleService.get_upcoming_interviews(request.user, days)
        serializer = InterviewScheduleListSerializer(schedules, many=True)
        return Response(serializer.data)


class FeaturedTipsView(APIView):
    """Get featured interview tips."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        tips = TipService.get_featured_tips()
        serializer = InterviewTipSerializer(tips, many=True)
        return Response(serializer.data)


class PracticeStatsView(APIView):
    """Get practice statistics."""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get stats."""
        stats = StatsService.get_practice_stats(request.user)
        serializer = PracticeStatsSerializer(stats)
        return Response(serializer.data)


# ============================================================================
# Interview Rounds (Frontend-facing)
# ============================================================================


class InterviewRoundDetailView(APIView):
    """Get details and questions for a specific interview round (session)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, round_id):
        """Return round detail matching an InterviewSession."""
        try:
            session = InterviewSession.objects.prefetch_related(
                "responses__question"
            ).get(id=round_id, user=request.user)
        except InterviewSession.DoesNotExist:
            return Response({"detail": "Round not found."}, status=status.HTTP_404_NOT_FOUND)

        # Build InterviewRoundDetail shape expected by frontend
        questions = []
        hosted_ai = HostedInterviewAIService()
        target_role = (session.target_career.title if session.target_career else (session.target_company or "")).strip()
        question_type_set = {str(q).lower() for q in (session.question_types or [])}
        is_technical_screening = question_type_set == {"technical", "coding"}
        for resp in session.responses.order_by("order"):
            q = resp.question
            options: list[str] = []
            prompt = q.question
            question_type = "text"

            if q.question_type == "coding":
                question_type = "coding"
            elif q.question_type == "technical":
                if is_technical_screening:
                    existing_analysis = resp.ai_analysis if isinstance(resp.ai_analysis, dict) else {}
                    stored_mcq = existing_analysis.get("round_mcq") if isinstance(existing_analysis, dict) else None

                    mcq_payload = None
                    if isinstance(stored_mcq, dict):
                        stored_options = stored_mcq.get("options") if isinstance(stored_mcq.get("options"), list) else []
                        stored_options = [str(opt).strip() for opt in stored_options if str(opt).strip()]
                        stored_correct = str(stored_mcq.get("correct_option") or "").strip()
                        if len(stored_options) == 4 and stored_correct in stored_options:
                            mcq_payload = {
                                "stem": q.question,
                                "options": stored_options,
                                "correct_option": stored_correct,
                                "explanation": str(stored_mcq.get("explanation") or "").strip(),
                            }

                    if not mcq_payload:
                        mcq_payload = hosted_ai.generate_mcq(
                            prompt=q.question,
                            target_role=target_role,
                            difficulty=session.difficulty_preference,
                        )

                    if mcq_payload:
                        question_type = "mcq"
                        prompt = mcq_payload.get("stem") or q.question
                        options = mcq_payload.get("options") or []

                        analysis = resp.ai_analysis if isinstance(resp.ai_analysis, dict) else {}
                        analysis["round_mcq"] = {
                            "correct_option": mcq_payload.get("correct_option", ""),
                            "options": options,
                            "explanation": mcq_payload.get("explanation", ""),
                        }
                        resp.ai_analysis = analysis
                        resp.save(update_fields=["ai_analysis"])

            questions.append({
                "question_id": str(resp.id),
                "type": question_type,
                "prompt": prompt,
                "options": options,
                "max_score": 100,
            })

        return Response({
            "round_id": str(session.id),
            "type": session.session_type,
            "instructions": session.ai_feedback or f"Answer all {session.num_questions} questions to the best of your ability.",
            "questions": questions,
            "status": session.status,
        })


class InterviewRoundSubmitView(APIView):
    """Submit answers for an interview round."""

    permission_classes = [IsAuthenticated]

    def post(self, request, round_id):
        """Accept answer submissions, save each answer, then complete the session."""
        try:
            session = InterviewSession.objects.prefetch_related(
                'responses'
            ).get(id=round_id, user=request.user)
        except InterviewSession.DoesNotExist:
            return Response({"detail": "Round not found."}, status=status.HTTP_404_NOT_FOUND)

        # Save and evaluate each answer keyed by response id (question_id in the event shape)
        answers = request.data.get("answers", [])
        answer_map = {
            str(a['question_id']): a.get('answer', '')
            for a in answers
            if isinstance(a, dict) and 'question_id' in a
        }

        evaluated_count = 0
        hosted_ai = HostedInterviewAIService()

        def _normalize_option_text(value: str) -> str:
            return " ".join(str(value).strip().lower().replace("\n", " ").split())

        for resp in session.responses.all():
            text = str(answer_map.get(str(resp.id), '') or '').strip()
            if not text:
                continue

            resp = ResponseService.submit_response(
                resp,
                response_text=text,
                time_taken_seconds=0,
                self_notes="input_mode:text|round_submit",
            )

            analysis = resp.ai_analysis if isinstance(resp.ai_analysis, dict) else {}
            mcq_meta = analysis.get("round_mcq") if isinstance(analysis, dict) else None
            if isinstance(mcq_meta, dict) and mcq_meta.get("correct_option"):
                options = mcq_meta.get("options") if isinstance(mcq_meta.get("options"), list) else []
                options = [str(opt).strip() for opt in options if str(opt).strip()]
                correct_option = str(mcq_meta.get("correct_option", "")).strip()

                given_raw = text.strip()
                given = _normalize_option_text(given_raw)
                correct_normalized = _normalize_option_text(correct_option)

                if len(given_raw) == 1 and given_raw.upper() in ["A", "B", "C", "D"] and len(options) >= 4:
                    idx = ord(given_raw.upper()) - ord("A")
                    if idx < len(options):
                        given = _normalize_option_text(options[idx])

                is_correct = given == correct_normalized

                resp.ai_score = 100 if is_correct else 35
                resp.content_score = resp.ai_score
                resp.structure_score = 100 if is_correct else 50
                resp.clarity_score = 100 if is_correct else 60
                resp.relevance_score = 100 if is_correct else 60
                resp.ai_feedback = (
                    "Correct. Full marks awarded." if is_correct else f"Incorrect. Correct option: {mcq_meta.get('correct_option')}"
                )
                analysis["evaluation_method"] = "round_mcq_objective"
                analysis["is_correct"] = is_correct
                resp.ai_analysis = analysis
                resp.save(update_fields=[
                    "ai_score", "content_score", "structure_score", "clarity_score",
                    "relevance_score", "ai_feedback", "ai_analysis",
                ])
            elif resp.question and resp.question.question_type == InterviewQuestion.QuestionType.CODING:
                coding_eval = hosted_ai.evaluate_coding_solution(
                    question=resp.question.question,
                    answer=text,
                    difficulty=session.difficulty_preference,
                    coding_language="python",
                    reference_solution=resp.question.sample_answer or "",
                )

                if coding_eval:
                    raw_score = coding_eval.get("score", 0)
                    try:
                        score = float(raw_score)
                    except (TypeError, ValueError):
                        score = 0.0

                    if score <= 1.0:
                        score *= 100.0
                    elif score <= 10.0:
                        score *= 10.0
                    score = int(max(0, min(100, round(score))))

                    is_correct = bool(coding_eval.get("is_correct", False))
                    resp.ai_score = score
                    resp.content_score = score
                    resp.structure_score = max(50, score - 5)
                    resp.clarity_score = max(50, score - 5)
                    resp.relevance_score = score
                    raw_feedback = str(coding_eval.get("feedback") or "").strip()
                    prefix = "Correct." if is_correct else "Incorrect."
                    if is_correct and score >= 95:
                        prefix = "Correct. Full marks awarded."
                    resp.ai_feedback = f"{prefix} {raw_feedback}".strip()

                    analysis["evaluation_method"] = "round_coding_objective"
                    analysis["is_correct"] = is_correct
                    analysis["issues"] = coding_eval.get("issues", [])
                    analysis["suggestions"] = coding_eval.get("suggestions", [])
                    analysis["strengths"] = coding_eval.get("strengths", [])
                    analysis["time_complexity"] = coding_eval.get("time_complexity", "")
                    analysis["space_complexity"] = coding_eval.get("space_complexity", "")
                    resp.ai_analysis = analysis
                    resp.save(update_fields=[
                        "ai_score", "content_score", "structure_score", "clarity_score",
                        "relevance_score", "ai_feedback", "ai_analysis",
                    ])
                else:
                    resp = ResponseService.evaluate_response_with_ai(resp)
            else:
                resp = ResponseService.evaluate_response_with_ai(resp)
            evaluated_count += 1

        # Transition through proper status flow: SCHEDULED â†’ IN_PROGRESS â†’ COMPLETED
        if session.status == InterviewSession.SessionStatus.SCHEDULED:
            session.status = InterviewSession.SessionStatus.IN_PROGRESS
            session.started_at = timezone.now()
            session.save(update_fields=['status', 'started_at'])

        try:
            session = SessionService.complete_session(session)
        except Exception as _err:
            logger.warning(f"Session complete failed for {round_id}: {_err}")

        return Response({
            "detail": "Answers submitted.",
            "session_id": str(session.id),
            "evaluated_answers": evaluated_count,
            "overall_score": session.overall_score,
            "ai_feedback": session.ai_feedback or "",
        })


class InterviewRoundFeedbackView(APIView):
    """Get AI feedback for a completed interview round."""

    permission_classes = [IsAuthenticated]

    def get(self, request, round_id):
        """Return feedback for the session."""
        try:
            session = InterviewSession.objects.get(id=round_id, user=request.user)
        except InterviewSession.DoesNotExist:
            return Response({"detail": "Round not found."}, status=status.HTTP_404_NOT_FOUND)

        # Return feedback in InterviewRoundFeedback shape expected by frontend
        feedback = {
            "round_id": str(session.id),
            "score": session.overall_score or 0,
            "feedback": session.ai_feedback or "Session completed.",
            "strengths": session.strengths or [],
            "improvements": session.improvements or [],
        }
        return Response(feedback)


# ============================================================================
# Confidence Metrics
# ============================================================================

class ConfidenceMetricsView(APIView):
    """Return the user's confidence trend derived from completed practice sessions."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.db.models import Avg, Sum

        user = request.user

        # Last 10 completed sessions ordered chronologically
        sessions = (
            InterviewSession.objects.filter(
                user=user,
                is_deleted=False,
                status=InterviewSession.SessionStatus.COMPLETED,
            )
            .order_by("completed_at")
            .prefetch_related("responses")[:10]
        )

        trend = []
        for s in sessions:
            agg = InterviewResponse.objects.filter(
                session=s, ai_score__isnull=False
            ).aggregate(avg=Avg("ai_score"))
            avg_score = agg["avg"]
            if avg_score is not None:
                trend.append(
                    {
                        "session_id": str(s.id),
                        "date": (
                            s.completed_at.isoformat()
                            if s.completed_at
                            else s.created_at.isoformat()
                        ),
                        "average_score": round(float(avg_score), 1),
                        "question_count": InterviewResponse.objects.filter(
                            session=s, completed_at__isnull=False
                        ).count(),
                    }
                )

        # Aggregate by question type across all responses
        responses = InterviewResponse.objects.filter(
            session__user=user, ai_score__isnull=False
        ).select_related("question")

        by_type: dict = {}
        for r in responses:
            qt = r.question.question_type
            if qt not in by_type:
                by_type[qt] = {"scores": [], "count": 0}
            by_type[qt]["scores"].append(float(r.ai_score))
            by_type[qt]["count"] += 1

        by_type_summary = {}
        for qt, d in by_type.items():
            avg = sum(d["scores"]) / len(d["scores"])
            by_type_summary[qt] = {
                "average_score": round(avg, 1),
                "count": d["count"],
                "confidence_level": (
                    "high" if avg >= 80 else "medium" if avg >= 60 else "low"
                ),
            }

        all_scores = [s for d in by_type.values() for s in d["scores"]]
        overall = round(sum(all_scores) / len(all_scores), 1) if all_scores else 0

        return Response(
            {
                "overall_confidence": overall,
                "trend": trend,
                "by_question_type": by_type_summary,
                "total_sessions": len(trend),
                "improvement_rate": (
                    round(
                        trend[-1]["average_score"] - trend[0]["average_score"], 1
                    )
                    if len(trend) >= 2
                    else 0
                ),
            }
        )
