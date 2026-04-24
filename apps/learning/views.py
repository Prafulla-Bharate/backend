"""
Learning Views
==============
API views for learning-related endpoints.
"""

import logging
import random
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from urllib.parse import quote_plus

from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction
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
    PhaseInjection,
    ProjectSubmission,
    CertificateVerification,
    SkillRefresherQuiz,
    UserLearningStreak,
    RetentionQuizQuestion,
    RetentionQuizAttempt,
)
from apps.learning.serializers import (
    LearningPathCreateSerializer,
    LearningPhaseSerializer,
    EnrollmentSerializer,
    ResourceProgressSerializer,
    ResourceProgressUpdateSerializer,
    CheckpointAttemptSerializer,
    SubmitAnswersSerializer,
    RecommendedResourceSerializer,
    LearningDashboardSerializer,
    LearningStatsSerializer,
    # New adaptive serializers
    PhaseInjectionSerializer,
    CompleteInjectionSerializer,
    ProjectSubmitSerializer,
    ProjectSubmissionSerializer,
    CertificateSubmitSerializer,
    CertificateVerificationSerializer,
    SkillRefresherSerializer,
    UserStreakSerializer,
    ComprehensiveStatsSerializer,
)
from apps.learning.services import (
    LearningPathService,
    EnrollmentService,
    ResourceProgressService,
    CheckpointService,
    RecommendationService,
    LearningStatsService,
    ProjectSubmissionService,
    CertificateVerificationService,
    SkillMasteryService,
    RefresherQuizService,
)

logger = logging.getLogger(__name__)


def _parse_bool_param(value) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _safe_list(value):
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def _first_nonempty(values, fallback=""):
    for v in values:
        if isinstance(v, str) and v.strip():
            return v.strip()
    return fallback


def _build_phase_youtube_videos(phase):
    queries = []
    queries.extend([q for q in _safe_list(phase.youtube_queries) if isinstance(q, str) and q.strip()])

    if not queries:
        base_terms = []
        base_terms.extend(_safe_list(phase.topics_covered)[:4])
        base_terms.extend(_safe_list(phase.skills_covered)[:3])
        base_terms.append(phase.title)
        for term in base_terms:
            text = str(term).strip()
            if text:
                queries.append(f"{text} tutorial 2026")

    deduped = []
    seen = set()
    for q in queries:
        key = str(q).strip().lower()
        if key and key not in seen:
            seen.add(key)
            deduped.append(str(q).strip())

    providers = ["YouTube", "freeCodeCamp", "Code With Mosh", "Traversy Media", "Fireship"]
    videos = []
    for i, query in enumerate(deduped[:8]):
        videos.append({
            "id": "",
            "title": f"{query} - practical guide",
            "channel_title": providers[i % len(providers)],
            "thumbnail_url": "",
            "published_at": "",
            "duration_minutes": 20 + (i * 10),
            "view_count": 10000 + (i * 3500),
            "description": f"Targeted video search for {query}",
            "_query": query,
        })
    return videos


def _build_phase_external_links(phase):
    colors = {
        "geeksforgeeks": "#0F9D58",
        "tutorialspoint": "#2A9D8F",
        "freecodecamp": "#0A0A23",
        "kaggle": "#20BEFF",
        "dev.to": "#111111",
        "docs": "#2563EB",
    }
    domains = {
        "geeksforgeeks": "geeksforgeeks.org",
        "tutorialspoint": "tutorialspoint.com",
        "freecodecamp": "freecodecamp.org",
        "kaggle": "kaggle.com",
        "dev.to": "dev.to",
        "docs": "docs",
    }

    links = []
    raw_topics = _safe_list(phase.external_topics)
    for item in raw_topics:
        if isinstance(item, dict):
            site = str(item.get("site", "Docs")).strip() or "Docs"
            topic = str(item.get("topic", "")).strip() or phase.title
        else:
            site = "Docs"
            topic = str(item).strip() or phase.title

        site_key = site.lower()
        if "geeks" in site_key:
            url = f"https://www.geeksforgeeks.org/?s={quote_plus(topic)}"
            normalized = "GeeksForGeeks"
            key = "geeksforgeeks"
        elif "tutorial" in site_key:
            url = f"https://www.tutorialspoint.com/index.htm?search={quote_plus(topic)}"
            normalized = "TutorialsPoint"
            key = "tutorialspoint"
        elif "freecodecamp" in site_key:
            url = f"https://www.freecodecamp.org/news/search/?query={quote_plus(topic)}"
            normalized = "freeCodeCamp"
            key = "freecodecamp"
        elif "kaggle" in site_key:
            url = f"https://www.kaggle.com/search?q={quote_plus(topic)}"
            normalized = "Kaggle"
            key = "kaggle"
        elif "dev" in site_key:
            url = f"https://dev.to/search?q={quote_plus(topic)}"
            normalized = "dev.to"
            key = "dev.to"
        else:
            url = f"https://www.google.com/search?q={quote_plus(topic + ' official docs tutorial')}"
            normalized = "Docs"
            key = "docs"

        links.append({
            "site": normalized,
            "domain": domains.get(key, "web"),
            "color": colors.get(key, "#2563EB"),
            "topic": topic,
            "url": url,
        })

    if not links:
        for topic in (_safe_list(phase.topics_covered)[:5] or _safe_list(phase.skills_covered)[:5] or [phase.title]):
            topic_str = str(topic).strip()
            if not topic_str:
                continue
            links.append({
                "site": "Docs",
                "domain": "web",
                "color": "#2563EB",
                "topic": topic_str,
                "url": f"https://www.google.com/search?q={quote_plus(topic_str + ' documentation tutorial')}",
            })
    return links[:10]


def _normalize_phase_certifications(phase):
    certs = []
    for item in _safe_list(phase.recommended_certifications):
        if not isinstance(item, dict):
            continue
        name = _first_nonempty([item.get("name"), item.get("title")], "Certification")
        platform = _first_nonempty([item.get("platform"), item.get("provider")], "Provider")
        search_query = _first_nonempty([
            item.get("search_query"),
            item.get("query"),
            f"{name} {platform}",
        ])
        url = _first_nonempty([
            item.get("url"),
            f"https://www.google.com/search?q={quote_plus(search_query)}",
        ])
        certs.append({
            "name": name,
            "platform": platform,
            "url": url,
            "is_free": bool(item.get("is_free", False)),
            "relevance": _first_nonempty([item.get("relevance"), "Validates practical, interview-relevant skills."]),
        })

    if certs:
        return certs[:6]

    base = _first_nonempty([phase.title, "Role"])
    return [
        {
            "name": f"{base} Professional Certificate",
            "platform": "Coursera",
            "url": f"https://www.google.com/search?q={quote_plus(base + ' professional certificate coursera')}",
            "is_free": False,
            "relevance": "Recognized credential aligned with this phase outcomes.",
        },
        {
            "name": f"{base} Hands-on Certification",
            "platform": "Udemy",
            "url": f"https://www.google.com/search?q={quote_plus(base + ' practical certification udemy')}",
            "is_free": False,
            "relevance": "Project-based certification to strengthen portfolio credibility.",
        },
    ]


def _fallback_deep_dive(phase):
    topics = []
    topic_seeds = _safe_list(phase.topics_covered)[:6] or _safe_list(phase.skills_covered)[:6] or [phase.title]
    for topic in topic_seeds:
        topic_text = str(topic).strip()
        if not topic_text:
            continue
        topics.append({
            "title": topic_text,
            "description": f"Build practical confidence in {topic_text} with project-first learning.",
            "subtopics": [
                f"{topic_text} fundamentals",
                f"{topic_text} implementation patterns",
                f"{topic_text} debugging and best practices",
            ],
            "estimated_hours": max(2, int((phase.estimated_hours or 8) / max(len(topic_seeds), 1))),
            "difficulty": phase.difficulty or "intermediate",
            "why_important": f"{topic_text} is directly used in real project delivery and interviews.",
        })

    project_title = f"{phase.title} Applied Project"
    return {
        "overview": phase.description or f"Deep-dive roadmap for {phase.title} with practical, job-ready outcomes.",
        "topics": topics,
        "projects": [
            {
                "title": project_title,
                "difficulty": phase.difficulty or "intermediate",
                "description": "Build an end-to-end practical project that demonstrates this phase competencies.",
                "deliverables": [
                    "Clean GitHub repository with documented architecture",
                    "README with setup, trade-offs, and outcomes",
                    "Short demo video or screenshots",
                ],
                "skills_demonstrated": (_safe_list(phase.skills_covered)[:6] or [phase.title]),
                "estimated_hours": max(8, int((phase.estimated_hours or 12) * 0.5)),
                "dataset_or_api": "Public dataset or free-tier API relevant to the phase",
                "github_search_query": f"{phase.title} project example",
                "real_world_relevance": "Simulates production-style work expected during interviews and on the job.",
            }
        ],
        "certifications": [
            {
                "name": f"{phase.title} Career Certificate",
                "platform": "Coursera",
                "search_query": f"{phase.title} certificate",
                "is_free": False,
                "estimated_cost_usd": 39,
                "time_to_complete_weeks": 4,
                "industry_value": "Provides resume signal for recruiters.",
                "prerequisite": "Basic familiarity with phase fundamentals",
            }
        ],
        "interview_questions": _safe_list(phase.interview_questions),
        "readiness_checklist": _safe_list(phase.readiness_checklist),
        "common_mistakes": [
            "Skipping fundamentals and jumping directly to tools",
            "Building projects without testing and documentation",
            "Ignoring error handling and maintainability",
        ],
        "real_world_applications": [
            f"Apply {phase.title} skills in a portfolio project",
            "Translate implementation decisions into interview-ready explanations",
            "Use measurable outcomes to strengthen resume impact",
        ],
        "next_phase_preview": "Next phase builds on these fundamentals with more complex, production-like scenarios.",
        "is_generating": False,
    }


def _normalize_capstone(phase):
    if isinstance(phase.capstone_project, dict) and phase.capstone_project.get("title"):
        return phase.capstone_project
    return {
        "title": f"Capstone: {phase.title} Implementation",
        "description": "Build a complete practical solution demonstrating this phase outcomes in a portfolio-ready format.",
        "deliverables": [
            "Production-style code repository",
            "Detailed README with architecture and results",
            "Demo walkthrough",
        ],
        "skills_demonstrated": _safe_list(phase.skills_covered)[:8],
        "estimated_hours": max(8, int((phase.estimated_hours or 12) * 0.6)),
        "difficulty_level": phase.difficulty or "intermediate",
        "github_search_query": f"{phase.title} capstone project",
    }


def _normalize_token_set(values):
    tokens = set()
    for value in values or []:
        if not value:
            continue
        text = str(value).strip().lower()
        if not text:
            continue
        tokens.add(text)
        for part in text.replace("/", " ").replace("-", " ").split():
            part = part.strip().lower()
            if len(part) > 2:
                tokens.add(part)
    return tokens


def _career_track_matches(user_career: str, question_tracks) -> bool:
    """Return True when a question career-track reasonably matches the user career title."""
    if not question_tracks:
        return True

    user_text = str(user_career or "").strip().lower()
    if not user_text:
        return True

    normalized_tracks = [
        str(track).strip().lower()
        for track in (question_tracks or [])
        if str(track).strip()
    ]
    if not normalized_tracks:
        return True

    # 1) Exact phrase match
    if user_text in normalized_tracks:
        return True

    # 2) Substring containment for close title variants
    # e.g. "machine learning engineer" <-> "junior machine learning engineer"
    for track in normalized_tracks:
        if track in user_text or user_text in track:
            return True

    # 3) Token-overlap match with generic-role tokens removed
    generic_tokens = {
        "engineer", "developer", "analyst", "specialist",
        "associate", "junior", "senior", "lead", "intern",
        "trainee", "expert", "principal", "staff",
    }
    user_tokens = {
        token for token in _normalize_token_set([user_text])
        if len(token) > 2 and token not in generic_tokens
    }

    for track in normalized_tracks:
        track_tokens = {
            token for token in _normalize_token_set([track])
            if len(token) > 2 and token not in generic_tokens
        }
        if user_tokens and track_tokens and len(user_tokens.intersection(track_tokens)) >= 2:
            return True

    return False


def _mark_phase_in_progress(enrollment, phase):
    """Persist phase start so frontend sees Continue instead of Start next time."""
    changed_fields = []

    if enrollment.current_phase_id != phase.id:
        enrollment.current_phase = phase
        changed_fields.append("current_phase")

    if enrollment.status == UserLearningPathEnrollment.EnrollmentStatus.ENROLLED:
        enrollment.status = UserLearningPathEnrollment.EnrollmentStatus.IN_PROGRESS
        changed_fields.append("status")
        if not enrollment.started_at:
            enrollment.started_at = timezone.now()
            changed_fields.append("started_at")

    enrollment.last_activity_at = timezone.now()
    changed_fields.append("last_activity_at")

    if changed_fields:
        enrollment.save(update_fields=changed_fields)


def _normalize_phrase_set(values):
    phrases = set()
    for value in values or []:
        if not value:
            continue
        text = str(value).strip().lower()
        if text:
            phrases.add(text)
    return phrases


def _meaningful_token_set(values):
    generic_tokens = {
        "and", "for", "with", "from", "into", "using", "use", "based",
        "data", "model", "models", "system", "systems", "solution", "solutions",
        "engineer", "engineering", "developer", "development", "analyst",
        "intro", "introduction", "basics", "fundamentals", "advanced", "beginner",
        "intermediate", "project", "projects", "career", "phase", "learning",
    }
    tokens = set()
    for token in _normalize_token_set(values):
        if len(token) <= 2:
            continue
        if token in generic_tokens:
            continue
        tokens.add(token)
    return tokens


def _question_topic_relevance(question, allowed_phrases, allowed_tokens):
    question_values = [question.topic, question.subtopic, *(question.tags or [])]
    question_phrases = _normalize_phrase_set(question_values)
    question_tokens = _meaningful_token_set(question_values)

    phrase_hits = len(question_phrases.intersection(allowed_phrases))
    token_hits = len(question_tokens.intersection(allowed_tokens))

    if phrase_hits > 0:
        return 100 + token_hits
    return token_hits


class GenerateLearningPathView(APIView):
    """Generate personalized learning path."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Create personalized learning path.

        When a user re-accepts a career this endpoint is called again with a
        new career.  We must drop any existing active enrollment first so the
        frontend immediately sees the new path as the active one.
        """
        serializer = LearningPathCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        from apps.learning.models import UserLearningPathEnrollment as _Enroll

        # Generate first, then switch active enrollment only if generation succeeds.
        with transaction.atomic():
            path = LearningPathService.generate_personalized_path(
                user=request.user,
                **serializer.validated_data
            )

            # Guardrail: do not enroll into broken/empty paths.
            if not path.phases.exists():
                path.delete()
                return Response(
                    {
                        "detail": "Learning path generation failed. Please retry.",
                        "code": "path_generation_incomplete",
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            enrollment = EnrollmentService.enroll_user(request.user, path)

            # Drop prior active enrollments ONLY after valid new enrollment exists.
            _Enroll.objects.filter(
                user=request.user,
                status__in=[
                    _Enroll.EnrollmentStatus.ENROLLED,
                    _Enroll.EnrollmentStatus.IN_PROGRESS,
                    _Enroll.EnrollmentStatus.PAUSED,
                ],
            ).exclude(id=enrollment.id).update(status=_Enroll.EnrollmentStatus.DROPPED)

        return Response(
            EnrollmentSerializer(enrollment, context={"request": request}).data,
            status=status.HTTP_201_CREATED
        )


# ============================================================================
# Enrollment Views
# ============================================================================

class EnrollmentViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for user enrollments."""
    
    permission_classes = [IsAuthenticated]
    ordering = "-created_at"  # required so global OrderingFilter returns a valid value for cursor pagination
    
    def get_queryset(self):
        """Return enrollments for current user — active only by default."""
        from apps.learning.models import UserLearningPathEnrollment as _E
        status_filter = self.request.query_params.get("status")
        qs = EnrollmentService.get_user_enrollments(
            self.request.user,
            status=status_filter,
        )
        # Unless the caller explicitly requests dropped/completed records,
        # hide them so the frontend never picks up a stale old enrollment
        # as the active path.
        if not status_filter:
            qs = qs.exclude(status__in=[
                _E.EnrollmentStatus.DROPPED,
                _E.EnrollmentStatus.COMPLETED,
            ])
        return qs

    def get_serializer_context(self):
        """Ensure request is always in serializer context (needed by nested path serializer)."""
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx
    
    def get_serializer_class(self):
        """Return appropriate serializer."""
        return EnrollmentSerializer


class ResourceProgressView(APIView):
    """Update progress on a resource."""
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request, resource_id):
        """Update progress."""
        try:
            resource = LearningResource.objects.get(id=resource_id)
        except LearningResource.DoesNotExist:
            return Response(
                {"detail": "Resource not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = ResourceProgressUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Get enrollment if resource is part of a path
        enrollment = None
        if resource.phase:
            enrollment = UserLearningPathEnrollment.objects.filter(
                user=request.user,
                learning_path=resource.phase.learning_path
            ).first()
        
        progress = ResourceProgressService.update_progress(
            request.user,
            resource,
            enrollment,
            **serializer.validated_data
        )
        
        return Response(ResourceProgressSerializer(progress).data)


class BookmarkedResourcesView(APIView):
    """Get bookmarked resources."""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get user's bookmarked resources."""
        bookmarks = ResourceProgressService.get_user_bookmarks(request.user)
        serializer = ResourceProgressSerializer(bookmarks, many=True)
        return Response(serializer.data)


# ============================================================================
# Checkpoint Views
# ============================================================================

class SubmitCheckpointView(APIView):
    """Submit checkpoint answers."""
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request, checkpoint_id):
        """Submit answers."""
        try:
            checkpoint = KnowledgeCheckpoint.objects.select_related("phase").get(
                id=checkpoint_id
            )
        except KnowledgeCheckpoint.DoesNotExist:
            return Response(
                {"detail": "Checkpoint not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = SubmitAnswersSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Get enrollment
        enrollment = None
        if checkpoint.phase:
            enrollment = UserLearningPathEnrollment.objects.filter(
                user=request.user,
                learning_path=checkpoint.phase.learning_path
            ).first()
        
        try:
            attempt = CheckpointService.submit_answers(
                request.user,
                checkpoint,
                serializer.validated_data["answers"],
                enrollment
            )
            
            return Response(CheckpointAttemptSerializer(attempt).data)
        
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


# ============================================================================
# Recommendation Views
# ============================================================================

class RecommendationsView(APIView):
    """Get learning recommendations."""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get recommendations."""
        limit = int(request.query_params.get("limit", 10))
        recommendations = RecommendationService.get_user_recommendations(
            request.user,
            limit=limit
        )
        serializer = RecommendedResourceSerializer(recommendations, many=True)
        return Response(serializer.data)


# ============================================================================
# Dashboard Views
# ============================================================================

class LearningDashboardView(APIView):
    """Get learning dashboard summary."""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get dashboard data."""
        user = request.user
        
        # Active enrollments
        active_enrollments = UserLearningPathEnrollment.objects.filter(
            user=user,
            status__in=[
                UserLearningPathEnrollment.EnrollmentStatus.ENROLLED,
                UserLearningPathEnrollment.EnrollmentStatus.IN_PROGRESS
            ]
        ).select_related("learning_path")[:5]
        
        # Completed count
        completed_count = UserLearningPathEnrollment.objects.filter(
            user=user,
            status=UserLearningPathEnrollment.EnrollmentStatus.COMPLETED
        ).count()
        
        # Total time
        from django.db.models import Sum
        total_time = UserLearningPathEnrollment.objects.filter(
            user=user
        ).aggregate(total=Sum("total_time_spent_minutes"))["total"] or 0
        
        # Skills learned
        skills_learned = set()
        completed_paths = UserLearningPathEnrollment.objects.filter(
            user=user,
            status=UserLearningPathEnrollment.EnrollmentStatus.COMPLETED
        ).select_related("learning_path")
        
        for enrollment in completed_paths:
            skills_learned.update(enrollment.learning_path.skills_covered)
        
        # Recommendations
        recommendations = RecommendationService.get_user_recommendations(user, limit=5)
        
        # Recent activity
        recent = UserResourceProgress.objects.filter(
            user=user
        ).select_related("resource").order_by("-updated_at")[:5]
        
        recent_activity = [
            {
                "type": "resource_progress",
                "resource_title": r.resource.title,
                "status": r.status,
                "timestamp": r.updated_at.isoformat()
            }
            for r in recent
        ]
        
        data = {
            "active_enrollments": active_enrollments,
            "completed_count": completed_count,
            "total_time_spent_hours": total_time // 60,
            "skills_learned": list(skills_learned),
            "recommendations": recommendations,
            "recent_activity": recent_activity
        }
        
        serializer = LearningDashboardSerializer(data)
        return Response(serializer.data)


class LearningStatsView(APIView):
    """Get learning statistics."""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get stats."""
        stats = LearningStatsService.get_user_stats(request.user)
        serializer = LearningStatsSerializer(stats)
        return Response(serializer.data)


class PhaseDetailView(APIView):
    """Return enriched details for a learning phase used by frontend phase page."""

    permission_classes = [IsAuthenticated]

    def get(self, request, phase_id):
        try:
            phase = LearningPhase.objects.select_related("learning_path").prefetch_related(
                "resources", "checkpoints"
            ).get(id=phase_id)
        except LearningPhase.DoesNotExist:
            return Response({"detail": "Phase not found."}, status=status.HTTP_404_NOT_FOUND)

        enrollment = UserLearningPathEnrollment.objects.filter(
            user=request.user,
            learning_path=phase.learning_path,
        ).first()

        if enrollment and str(phase.id) not in [str(p) for p in (enrollment.completed_phases or [])]:
            _mark_phase_in_progress(enrollment, phase)

        refresh = _parse_bool_param(request.query_params.get("refresh"))

        deep_dive_content = phase.deep_dive_content if isinstance(phase.deep_dive_content, dict) else {}
        if refresh or not deep_dive_content or not deep_dive_content.get("topics"):
            try:
                timeout_seconds = 4
                executor = ThreadPoolExecutor(max_workers=1)
                future = executor.submit(
                    LearningPathService.generate_phase_deep_dive,
                    phase,
                    request.user,
                )
                try:
                    generated = future.result(timeout=timeout_seconds)
                finally:
                    executor.shutdown(wait=False, cancel_futures=True)
                if isinstance(generated, dict) and generated:
                    deep_dive_content = generated
            except FuturesTimeoutError:
                logger.warning(
                    f"Deep-dive generation timed out for phase {phase.id}; serving fallback payload."
                )
            except Exception as exc:
                logger.warning(f"Deep-dive generation failed for phase {phase.id}: {exc}")

        serialized_phase = LearningPhaseSerializer(phase, context={"request": request}).data

        # Build flattened resource list with completion flags expected by frontend.
        completed_resource_ids = set(
            UserResourceProgress.objects.filter(
                user=request.user,
                resource__phase=phase,
                status=UserResourceProgress.ProgressStatus.COMPLETED,
            ).values_list("resource_id", flat=True)
        )

        resources = []
        for item in serialized_phase.get("resources", []):
            item = dict(item)
            item["is_completed"] = str(item.get("id")) in {str(rid) for rid in completed_resource_ids}
            item["source"] = item.get("source") or "db"
            resources.append(item)

        deep_dive_payload = deep_dive_content or _fallback_deep_dive(phase)
        youtube_videos = _build_phase_youtube_videos(phase)
        external_links = _build_phase_external_links(phase)
        certifications = _normalize_phase_certifications(phase)
        capstone = _normalize_capstone(phase)

        response_data = {
            "id": str(phase.id),
            "path_id": str(phase.learning_path_id),
            "path_title": phase.learning_path.title,
            "title": phase.title,
            "description": phase.description,
            "order": phase.order,
            "estimated_hours": phase.estimated_hours,
            "difficulty": phase.difficulty,
            "skills_covered": phase.skills_covered or [],
            "topics_covered": phase.topics_covered or [],
            "phase_outcome": phase.phase_outcome or "",
            "learning_objectives": phase.learning_objectives or [],
            "prerequisite_skills": phase.prerequisite_skills or [],
            "readiness_checklist": phase.readiness_checklist or [],
            "interview_questions": phase.interview_questions or [],
            "status": serialized_phase.get("status", "not_started"),
            "is_completed": serialized_phase.get("is_completed", False),
            "resources": resources,
            "checkpoints": serialized_phase.get("checkpoints", []),
            "deep_dive_resources": [r for r in resources if r.get("source") == "deep_dive"],
            "youtube_videos": youtube_videos,
            "external_links": external_links,
            "certifications": certifications,
            "capstone_project": capstone,
            "deep_dive": deep_dive_payload,
        }

        return Response(response_data)


class StartRetentionQuizView(APIView):
    """Start a pre-phase retention quiz using topics from previous phases."""

    permission_classes = [IsAuthenticated]

    QUIZ_SIZE = 5
    PASSING_SCORE = 70

    def post(self, request, phase_id):
        try:
            target_phase = LearningPhase.objects.select_related("learning_path").get(id=phase_id)
        except LearningPhase.DoesNotExist:
            return Response({"error": "Phase not found"}, status=status.HTTP_404_NOT_FOUND)

        enrollment = UserLearningPathEnrollment.objects.filter(
            user=request.user,
            learning_path=target_phase.learning_path,
        ).first()
        if not enrollment:
            return Response({"error": "Enrollment not found"}, status=status.HTTP_404_NOT_FOUND)

        completed_phase_ids = {str(pid) for pid in (enrollment.completed_phases or [])}
        if str(target_phase.id) in completed_phase_ids:
            _mark_phase_in_progress(enrollment, target_phase)
            return Response({
                "success": True,
                "data": {
                    "skip": True,
                    "reason": "Phase already completed.",
                },
            })

        if enrollment.current_phase_id and str(enrollment.current_phase_id) == str(target_phase.id):
            return Response({
                "success": True,
                "data": {
                    "skip": True,
                    "reason": "Phase already started.",
                },
            })

        existing_submitted = RetentionQuizAttempt.objects.filter(
            user=request.user,
            enrollment=enrollment,
            target_phase=target_phase,
            status=RetentionQuizAttempt.AttemptStatus.SUBMITTED,
        ).order_by("-submitted_at", "-created_at").first()

        if existing_submitted:
            _mark_phase_in_progress(enrollment, target_phase)
            return Response({
                "success": True,
                "data": {
                    "skip": True,
                    "reason": "Retention quiz already submitted for this phase.",
                },
            })

        existing_started = RetentionQuizAttempt.objects.filter(
            user=request.user,
            enrollment=enrollment,
            target_phase=target_phase,
            status=RetentionQuizAttempt.AttemptStatus.STARTED,
        ).order_by("-created_at").first()

        if existing_started and existing_started.questions_snapshot:
            client_questions = []
            for item in existing_started.questions_snapshot:
                client_questions.append({
                    "id": str(item.get("id")),
                    "topic": item.get("topic", ""),
                    "subtopic": item.get("subtopic", ""),
                    "difficulty": item.get("difficulty", "medium"),
                    "question_text": item.get("question_text", ""),
                    "options": item.get("options", []),
                })

            if client_questions:
                return Response({
                    "success": True,
                    "data": {
                        "skip": False,
                        "attempt_id": str(existing_started.id),
                        "passing_score": int(existing_started.passing_score or self.PASSING_SCORE),
                        "total_questions": len(client_questions),
                        "questions": client_questions,
                    },
                })

        previous_phases = list(
            target_phase.learning_path.phases.filter(order__lt=target_phase.order).order_by("order")
        )
        if not previous_phases:
            _mark_phase_in_progress(enrollment, target_phase)
            return Response({
                "success": True,
                "data": {
                    "skip": True,
                    "reason": "No previous phases available for retention quiz.",
                },
            })

        allowed_topics = []
        for phase in previous_phases:
            allowed_topics.extend(phase.skills_covered or [])
            allowed_topics.extend(phase.topics_covered or [])
            allowed_topics.append(phase.title)

        allowed_phrases = _normalize_phrase_set(allowed_topics)
        allowed_tokens = _meaningful_token_set(allowed_topics)

        weak_counter = Counter()
        previous_attempts = UserCheckpointAttempt.objects.filter(
            user=request.user,
            enrollment=enrollment,
            checkpoint__phase__learning_path=target_phase.learning_path,
            checkpoint__phase__order__lt=target_phase.order,
        ).order_by("-created_at")[:30]

        for attempt in previous_attempts:
            for _, item in (attempt.feedback or {}).items():
                if not item.get("is_correct"):
                    topic = str(item.get("topic", "")).strip().lower()
                    if topic:
                        weak_counter[topic] += 1

        weak_topics = set(weak_counter.keys())

        # ── Career track resolution (multiple fallbacks) ──────────────────
        # Try: 1) enrollment FK → 2) path title → 3) empty (skip filter)
        career_track = ""
        if enrollment.personalized_for_career:
            career_track = (enrollment.personalized_for_career.title or "").strip().lower()
        if not career_track:
            career_track = (target_phase.learning_path.title or "").strip().lower()

        all_questions = list(RetentionQuizQuestion.objects.filter(is_active=True))

        # ── Tiered candidate selection ─────────────────────────────────────
        # TIER 1: question has career_tracks AND matches user career
        #         + passes topic relevance check (>= 1 hit is fine since career already confirms relevance)
        # TIER 2: question has NO career_tracks (generic) AND topic relevance >= 2
        # SKIP:   question has career_tracks but does NOT match user career → always excluded
        tier1 = []  # (question, relevance) — career-confirmed, topic-relevant
        tier2 = []  # (question, relevance) — generic/untagged fallback

        for question in all_questions:
            has_career_label = bool(question.career_tracks)
            relevance = _question_topic_relevance(question, allowed_phrases, allowed_tokens)

            if has_career_label:
                # Career-labeled question: MUST match user career to be eligible
                if career_track and _career_track_matches(career_track, question.career_tracks):
                    if relevance >= 1:
                        tier1.append((question, relevance))
                # else: skip entirely — different career
            else:
                # No career label: use as fallback only if strongly topic-relevant
                if relevance >= 2:
                    tier2.append((question, relevance))

        # Sort best-relevance first, then shuffle within equal-relevance groups
        # so users don't always see the same top-N
        tier1.sort(key=lambda item: item[1], reverse=True)
        tier2.sort(key=lambda item: item[1], reverse=True)
        random.shuffle(tier1)
        random.shuffle(tier2)
        tier1.sort(key=lambda item: item[1], reverse=True)

        # Build combined pool: tier1 is preferred, tier2 only fills remaining slots
        candidate_questions = tier1 if tier1 else tier2

        if not candidate_questions:
            _mark_phase_in_progress(enrollment, target_phase)
            return Response({
                "success": True,
                "data": {
                    "skip": True,
                    "reason": "No retention quiz questions matched this career and topics.",
                },
            })

        # ── Split into weak (user got wrong before) vs normal ─────────────
        weak_pool = []
        normal_pool = []
        for question, relevance in candidate_questions:
            q_topics = _normalize_token_set([question.topic, question.subtopic, *(question.tags or [])])
            if weak_topics.intersection(q_topics):
                weak_pool.append((question, relevance))
            else:
                normal_pool.append((question, relevance))

        weak_quota = min(3, len(weak_pool), self.QUIZ_SIZE)
        selected_questions = [item[0] for item in weak_pool[:weak_quota]]
        remaining = self.QUIZ_SIZE - len(selected_questions)

        if remaining > 0:
            selected_questions.extend([item[0] for item in normal_pool[:remaining]])
            remaining = self.QUIZ_SIZE - len(selected_questions)

        if remaining > 0:
            leftovers = [
                item[0]
                for item in weak_pool[weak_quota:]
                if item[0].id not in {s.id for s in selected_questions}
            ]
            selected_questions.extend(leftovers[:remaining])

        # If tier1 was empty, fill from tier2 for remaining slots
        if not tier1 and tier2 and remaining > 0:
            tier2_ids = {s.id for s in selected_questions}
            selected_questions.extend([
                item[0] for item in tier2 if item[0].id not in tier2_ids
            ][:remaining])

        if not selected_questions:
            _mark_phase_in_progress(enrollment, target_phase)
            return Response({
                "success": True,
                "data": {
                    "skip": True,
                    "reason": "Unable to build retention quiz for this phase.",
                },
            })

        snapshot = []
        client_questions = []
        for question in selected_questions:
            snapshot_item = {
                "id": str(question.id),
                "topic": question.topic,
                "subtopic": question.subtopic,
                "difficulty": question.difficulty,
                "question_text": question.question_text,
                "options": question.options or [],
                "correct_answer": str(question.correct_answer),
                "explanation": question.explanation,
            }
            snapshot.append(snapshot_item)
            client_questions.append({
                "id": str(question.id),
                "topic": question.topic,
                "subtopic": question.subtopic,
                "difficulty": question.difficulty,
                "question_text": question.question_text,
                "options": question.options or [],
            })

        attempt = RetentionQuizAttempt.objects.create(
            user=request.user,
            enrollment=enrollment,
            target_phase=target_phase,
            passing_score=self.PASSING_SCORE,
            questions_snapshot=snapshot,
        )

        return Response({
            "success": True,
            "data": {
                "skip": False,
                "attempt_id": str(attempt.id),
                "passing_score": self.PASSING_SCORE,
                "total_questions": len(client_questions),
                "questions": client_questions,
            },
        })


class SubmitRetentionQuizView(APIView):
    """Submit and evaluate a pre-phase retention quiz attempt."""

    permission_classes = [IsAuthenticated]

    def post(self, request, phase_id):
        attempt_id = request.data.get("attempt_id")
        answers = request.data.get("answers", {}) or {}

        if not attempt_id:
            return Response({"error": "attempt_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        if not isinstance(answers, dict):
            return Response({"error": "answers must be an object"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            attempt = RetentionQuizAttempt.objects.select_related(
                "target_phase", "enrollment"
            ).get(
                id=attempt_id,
                user=request.user,
                target_phase_id=phase_id,
                status=RetentionQuizAttempt.AttemptStatus.STARTED,
            )
        except RetentionQuizAttempt.DoesNotExist:
            return Response({"error": "Retention quiz attempt not found"}, status=status.HTTP_404_NOT_FOUND)

        snapshot = attempt.questions_snapshot or []
        total = len(snapshot)
        if total == 0:
            return Response({"error": "No questions found for this attempt"}, status=status.HTTP_400_BAD_REQUEST)

        correct = 0
        weak_topics = set()
        result_items = []

        for item in snapshot:
            question_id = str(item.get("id"))
            user_answer = str(answers.get(question_id, ""))
            expected = str(item.get("correct_answer", ""))
            is_correct = user_answer and user_answer == expected
            if is_correct:
                correct += 1
            else:
                topic = str(item.get("topic", "")).strip()
                if topic:
                    weak_topics.add(topic)

            result_items.append({
                "id": question_id,
                "topic": item.get("topic", ""),
                "is_correct": bool(is_correct),
                "explanation": item.get("explanation", ""),
            })

        score = int((correct / total) * 100)
        passed = score >= int(attempt.passing_score or 70)

        attempt.answers = answers
        attempt.score = score
        attempt.passed = passed
        attempt.weak_topics = sorted(list(weak_topics))
        attempt.status = RetentionQuizAttempt.AttemptStatus.SUBMITTED
        attempt.submitted_at = timezone.now()
        attempt.save(update_fields=[
            "answers",
            "score",
            "passed",
            "weak_topics",
            "status",
            "submitted_at",
            "updated_at",
        ])

        used_ids = [item.get("id") for item in snapshot if item.get("id")]
        if used_ids:
            for question in RetentionQuizQuestion.objects.filter(id__in=used_ids):
                question.usage_count += 1
                question.save(update_fields=["usage_count", "updated_at"])

        remedial_injection = None
        if weak_topics:
            resources = []
            for topic in sorted(list(weak_topics))[:5]:
                q = topic.replace(" ", "+")
                resources.append({
                    "title": f"Revise: {topic}",
                    "url": f"https://www.google.com/search?q={q}+tutorial",
                    "type": "tutorial",
                    "platform": "Web Search",
                    "duration_minutes": 20,
                    "concept_covered": topic,
                })

            remedial_injection = PhaseInjection.objects.create(
                enrollment=attempt.enrollment,
                target_phase=attempt.target_phase,
                injection_type=PhaseInjection.InjectionType.REMEDIAL,
                title="Retention Quiz Remedial Topics",
                reason=(
                    f"Retention quiz score {score}%. Review weak topics before continuing this phase."
                ),
                weak_concepts=sorted(list(weak_topics)),
                injected_resources=resources,
                verification_quiz={},
                priority=2,
            )

        _mark_phase_in_progress(attempt.enrollment, attempt.target_phase)

        return Response({
            "success": True,
            "data": {
                "attempt_id": str(attempt.id),
                "score": score,
                "passed": passed,
                "passing_score": int(attempt.passing_score or 70),
                "weak_topics": sorted(list(weak_topics)),
                "results": result_items,
                "remedial_injection_added": remedial_injection is not None,
                "remedial_injection_id": str(remedial_injection.id) if remedial_injection else None,
            },
        })


# ============================================================================
# Adaptive Learning Views (Phase Injections)
# ============================================================================

class PhaseInjectionsView(APIView):
    """List adaptive phase injections for an enrollment."""

    permission_classes = [IsAuthenticated]

    def get(self, request, enrollment_id):
        try:
            enrollment = UserLearningPathEnrollment.objects.get(
                id=enrollment_id, user=request.user
            )
        except UserLearningPathEnrollment.DoesNotExist:
            return Response({"error": "Enrollment not found"}, status=status.HTTP_404_NOT_FOUND)

        injections = PhaseInjection.objects.filter(enrollment=enrollment).order_by(
            "-priority", "created_at"
        )
        serializer = PhaseInjectionSerializer(injections, many=True)
        return Response({"success": True, "data": serializer.data})


class CompleteInjectionView(APIView):
    """Mark a phase injection as completed (with optional quiz answers)."""

    permission_classes = [IsAuthenticated]

    def post(self, request, injection_id):
        try:
            injection = PhaseInjection.objects.get(
                id=injection_id, enrollment__user=request.user
            )
        except PhaseInjection.DoesNotExist:
            return Response({"error": "Injection not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = CompleteInjectionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        injection.is_completed = True
        injection.save(update_fields=["is_completed"])

        return Response({"success": True, "message": "Injection marked as complete."})


# ============================================================================
# Project Submission Views
# ============================================================================

class ProjectSubmitView(APIView):
    """Submit a project and run AI review."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ProjectSubmitSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            submission = ProjectSubmissionService.submit_project(
                user=request.user, **serializer.validated_data
            )
            return Response(
                {
                    "success": True,
                    "data": ProjectSubmissionSerializer(submission).data,
                    "message": "Project submitted and review processed successfully.",
                },
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            logger.error(f"Project submit failed: {e}", exc_info=True)
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ProjectListView(APIView):
    """List authenticated user's project submissions."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        submissions = ProjectSubmissionService.get_user_submissions(
            request.user, status=request.query_params.get("status")
        )
        return Response({"success": True, "data": ProjectSubmissionSerializer(submissions, many=True).data})


# ============================================================================
# Certificate Verification Views
# ============================================================================

class CertificateSubmitView(APIView):
    """Submit a certificate and run verification."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CertificateSubmitSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            verification = CertificateVerificationService.submit_certificate(
                user=request.user, **serializer.validated_data
            )
            return Response(
                {
                    "success": True,
                    "data": CertificateVerificationSerializer(verification).data,
                    "message": "Certificate submitted and verification processed successfully.",
                },
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            logger.error(f"Certificate submit failed: {e}", exc_info=True)
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CertificateListView(APIView):
    """List authenticated user's certificate verifications."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        certs = CertificateVerificationService.get_user_certificates(
            request.user, status=request.query_params.get("status")
        )
        return Response({"success": True, "data": CertificateVerificationSerializer(certs, many=True).data})


# ============================================================================
# Skill Refresher Views
# ============================================================================

class PendingRefreshersView(APIView):
    """List pending skill refresher quizzes for the authenticated user."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        refreshers = RefresherQuizService.get_pending_refreshers(request.user)
        return Response({"success": True, "data": SkillRefresherSerializer(refreshers, many=True).data})


# ============================================================================
# Streak & Comprehensive Stats Views
# ============================================================================

class UserStreakView(APIView):
    """Return the authenticated user's learning streak information."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        streak, _ = UserLearningStreak.objects.get_or_create(user=request.user)
        return Response({"success": True, "data": UserStreakSerializer(streak).data})


class ComprehensiveStatsView(APIView):
    """Full adaptive learning stats — skills, projects, certs, streaks."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # Core stats
        base = LearningStatsService.get_user_stats(user)

        # Skill summary
        skill_summary = SkillMasteryService.get_skill_summary(user)

        # Project stats
        from django.db.models import Avg as DjangoAvg
        project_qs = ProjectSubmission.objects.filter(user=user)
        projects = {
            "total": project_qs.count(),
            "reviewed": project_qs.exclude(status=ProjectSubmission.SubmissionStatus.SUBMITTED).count(),
            "average_score": round(
                float(project_qs.aggregate(a=DjangoAvg("overall_score"))["a"] or 0), 1
            ),
        }

        # Certificate stats
        cert_qs = CertificateVerification.objects.filter(user=user)
        certificates = {
            "total": cert_qs.count(),
            "verified": cert_qs.filter(
                status=CertificateVerification.VerificationStatus.VERIFIED
            ).count(),
        }

        # Adaptive learning (injections)
        injection_qs = PhaseInjection.objects.filter(enrollment__user=user)
        adaptive_learning = {
            "total_injections": injection_qs.count(),
            "completed": injection_qs.filter(is_completed=True).count(),
            "pending": injection_qs.filter(is_completed=False).count(),
        }

        # Refresher stats
        refresher_qs = SkillRefresherQuiz.objects.filter(user=user)
        skill_refreshers = {
            "total": refresher_qs.count(),
            "pending": refresher_qs.filter(
                status__in=[
                    SkillRefresherQuiz.QuizStatus.PENDING,
                    SkillRefresherQuiz.QuizStatus.SENT,
                ]
            ).count(),
            "completed": refresher_qs.filter(
                status=SkillRefresherQuiz.QuizStatus.COMPLETED
            ).count(),
        }

        # Streak
        streak_obj, _ = UserLearningStreak.objects.get_or_create(user=user)
        streak = {
            "current": streak_obj.current_streak,
            "longest": streak_obj.longest_streak,
            "total_active_days": streak_obj.total_active_days,
        }

        data = {
            **base,
            "skills": skill_summary,
            "projects": projects,
            "certificates": certificates,
            "adaptive_learning": adaptive_learning,
            "skill_refreshers": skill_refreshers,
            "streak": streak,
        }

        serializer = ComprehensiveStatsSerializer(data)
        return Response({"success": True, "data": serializer.data})
