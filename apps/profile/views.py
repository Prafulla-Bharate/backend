"""
Profile Views
=============
API views for profile-related endpoints.
"""

import logging
import re

from rest_framework import status, viewsets
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.profile.models import (
    UserEducation,
    UserExperience,
    UserCertification,
    UserProject,
    UserLanguage,
    UserSocialLink,
)
from apps.profile.serializers import (
    UserEducationSerializer,
    UserEducationListSerializer,
    UserExperienceSerializer,
    UserExperienceListSerializer,
    UserCertificationSerializer,
    UserProjectSerializer,
    UserLanguageSerializer,
    UserSocialLinkSerializer,
    ProfileCompletenessSerializer,
    UserProfileSerializer,
    ProfilePictureSerializer,
)
from apps.profile.services import (
    ProfileService,
    EducationService,
    ExperienceService,
)
from services.ai.gemini import get_gemini_service

logger = logging.getLogger(__name__)


def _extract_resume_text(uploaded_file) -> str:
    """Extract plain text from uploaded resume file."""
    filename = (getattr(uploaded_file, "name", "") or "").lower()
    ext = filename.rsplit(".", 1)[-1] if "." in filename else ""

    uploaded_file.seek(0)

    if ext == "pdf":
        # Prefer pdfplumber when available for better layout extraction,
        # but gracefully fall back to PyPDF2 if pdfplumber isn't installed.
        try:
            import pdfplumber

            uploaded_file.seek(0)
            with pdfplumber.open(uploaded_file) as pdf:
                parts = [(page.extract_text() or "") for page in pdf.pages]
            text = "\n".join(parts).strip()
            if text:
                return text
        except ModuleNotFoundError:
            logger.info("pdfplumber not installed; falling back to PyPDF2 for PDF extraction")
        except Exception as exc:
            logger.warning("pdfplumber extraction failed, trying PyPDF2 fallback: %s", exc)

        try:
            from PyPDF2 import PdfReader

            uploaded_file.seek(0)
            reader = PdfReader(uploaded_file)
            parts = [(page.extract_text() or "") for page in reader.pages]
            text = "\n".join(parts).strip()
            if text:
                return text
        except Exception as exc:
            logger.warning("PyPDF2 extraction failed, trying raw PDF text recovery: %s", exc)

        # Last-resort raw text recovery for tricky PDFs (scanned/producer quirks).
        # This can recover contact links and some plaintext from PDF content streams.
        uploaded_file.seek(0)
        raw_bytes = uploaded_file.read()
        if isinstance(raw_bytes, bytes) and raw_bytes:
            decoded = raw_bytes.decode("latin-1", errors="ignore")

            # Try extracting PDF string literals like (text) Tj
            literal_tokens = re.findall(r"\(([^()]{2,300})\)", decoded)
            literal_tokens = [t.strip() for t in literal_tokens if re.search(r"[A-Za-z0-9]", t)]
            literal_text = "\n".join(literal_tokens).strip()
            if len(literal_text) >= 40:
                return literal_text

            # Fallback: recover visible ASCII words/URLs from raw stream
            rough = re.sub(r"[^A-Za-z0-9@._:/+\-\s]", " ", decoded)
            rough = re.sub(r"\s+", " ", rough).strip()
            if len(rough) >= 80:
                return rough[:15000]

        raise ValueError("Unable to read this PDF clearly. Please try DOCX/TXT or a text-based PDF.")

    if ext == "docx":
        from docx import Document

        doc = Document(uploaded_file)
        return "\n".join([p.text for p in doc.paragraphs if p.text]).strip()

    if ext in {"txt", "md", "rtf", "doc"}:
        uploaded_file.seek(0)
        raw = uploaded_file.read()
        if isinstance(raw, bytes):
            return raw.decode("utf-8", errors="ignore").strip()
        return str(raw).strip()

    raise ValueError("Unsupported file type. Use PDF, DOCX, TXT, MD, DOC, or RTF.")


def _infer_experience_level(text: str) -> str:
    lowered = text.lower()
    year_match = re.search(r"(\d{1,2})\+?\s+years", lowered)
    if year_match:
        years = int(year_match.group(1))
        if years <= 1:
            return "entry"
        if years <= 4:
            return "mid"
        if years <= 9:
            return "senior"
        return "lead"
    if "intern" in lowered or "student" in lowered or "fresher" in lowered:
        return "student"
    return ""


def _heuristic_parse_resume(text: str) -> dict:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    head = lines[:40]
    joined_head = "\n".join(head)

    first_name = ""
    last_name = ""
    if lines:
        candidate = lines[0]
        if len(candidate.split()) in {2, 3} and "@" not in candidate and len(candidate) < 60:
            parts = candidate.split()
            first_name = parts[0]
            last_name = " ".join(parts[1:])

    phone_match = re.search(r"(\+?\d[\d\s\-()]{7,}\d)", joined_head)
    linkedin_match = re.search(r"https?://(?:www\.)?linkedin\.com/[^\s]+", text, re.IGNORECASE)
    github_match = re.search(r"https?://(?:www\.)?github\.com/[^\s]+", text, re.IGNORECASE)
    any_url_match = re.search(r"https?://[^\s]+", text, re.IGNORECASE)

    skills = []
    skills_match = re.search(r"skills?\s*[:\-]\s*(.+)", text, re.IGNORECASE)
    if skills_match:
        skills = [s.strip() for s in re.split(r",|\||/", skills_match.group(1)) if s.strip()][:20]

    bio = ""
    summary_match = re.search(r"(?:summary|profile|objective)\s*[:\-]?\s*(.+)", text, re.IGNORECASE)
    if summary_match:
        bio = summary_match.group(1).strip()[:400]
    elif len(lines) > 2:
        bio = " ".join(lines[1:4])[:400]

    payload = {
        "first_name": first_name,
        "last_name": last_name,
        "phone": phone_match.group(1).strip() if phone_match else "",
        "location": "",
        "bio": bio,
        "linkedin_url": linkedin_match.group(0).strip() if linkedin_match else "",
        "github_url": github_match.group(0).strip() if github_match else "",
        "portfolio_url": any_url_match.group(0).strip() if any_url_match else "",
        "experience_level": _infer_experience_level(text),
        "skills": skills,
        "interests": [],
        "career_goal": "",
        "target_roles": [],
        "education": [],
        "experience": [],
    }
    return payload


def _normalize_parsed_payload(payload: dict) -> dict:
    base = {
        "first_name": "",
        "last_name": "",
        "phone": "",
        "location": "",
        "bio": "",
        "linkedin_url": "",
        "github_url": "",
        "portfolio_url": "",
        "experience_level": "",
        "skills": [],
        "interests": [],
        "career_goal": "",
        "target_roles": [],
        "education": [],
        "experience": [],
    }
    if not isinstance(payload, dict):
        return base

    for key in [
        "first_name",
        "last_name",
        "phone",
        "location",
        "bio",
        "linkedin_url",
        "github_url",
        "portfolio_url",
        "experience_level",
        "career_goal",
    ]:
        value = payload.get(key, "")
        base[key] = value if isinstance(value, str) else ""

    for key in ["skills", "interests", "target_roles"]:
        value = payload.get(key, [])
        if isinstance(value, list):
            cleaned = [str(item).strip() for item in value if str(item).strip()]
            deduped = list(dict.fromkeys(cleaned))
            base[key] = deduped[:30]

    education = payload.get("education", [])
    if isinstance(education, list):
        cleaned_education = []
        for item in education[:10]:
            if not isinstance(item, dict):
                continue
            cleaned_education.append({
                "degree": str(item.get("degree", "") or "").strip(),
                "institution": str(item.get("institution", "") or "").strip(),
                "field": str(item.get("field", "") or "").strip(),
                "startYear": str(item.get("startYear", "") or "").strip(),
                "endYear": str(item.get("endYear", "") or "").strip(),
                "grade": str(item.get("grade", "") or "").strip(),
            })
        base["education"] = cleaned_education

    experience = payload.get("experience", [])
    if isinstance(experience, list):
        cleaned_experience = []
        for item in experience[:20]:
            if not isinstance(item, dict):
                continue
            cleaned_experience.append({
                "company": str(item.get("company", "") or "").strip(),
                "position": str(item.get("position", "") or "").strip(),
                "location": str(item.get("location", "") or "").strip(),
                "startDate": str(item.get("startDate", "") or "").strip(),
                "endDate": str(item.get("endDate", "") or "").strip(),
                "isCurrent": bool(item.get("isCurrent", False)),
                "description": str(item.get("description", "") or "").strip(),
            })
        base["experience"] = cleaned_experience

    return base


def _llm_parse_resume(text: str) -> dict | None:
    gemini = get_gemini_service()
    if not getattr(gemini, "is_configured", False):
        return None

    resume_snippet = text[:12000]
    prompt = f"""
Extract onboarding profile fields from this resume text and return ONLY valid JSON.

Schema:
{{
  "first_name": "",
  "last_name": "",
  "phone": "",
  "location": "",
  "bio": "",
  "linkedin_url": "",
  "github_url": "",
  "portfolio_url": "",
  "experience_level": "student|entry|mid|senior|lead|executive|",
  "skills": [""],
  "interests": [""],
  "career_goal": "",
  "target_roles": [""],
  "education": [
    {{
      "degree": "",
      "institution": "",
      "field": "",
      "startYear": "",
      "endYear": "",
      "grade": ""
    }}
  ],
  "experience": [
    {{
      "company": "",
      "position": "",
      "location": "",
      "startDate": "YYYY-MM or YYYY",
      "endDate": "YYYY-MM or YYYY",
      "isCurrent": false,
      "description": ""
    }}
  ]
}}

Rules:
- Output JSON only, no markdown.
- Keep unknown fields empty.
- `skills`, `interests`, and `target_roles` must be concise arrays.
- Infer `experience_level` from years of experience if possible.

Resume text:
{resume_snippet}
"""
    return gemini.generate_json(prompt)


class ResumeParsePreviewView(APIView):
    """Parse resume and return onboarding autofill data without saving profile."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        uploaded_file = request.FILES.get("file")
        if not uploaded_file:
            return Response({"detail": "Resume file is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            resume_text = _extract_resume_text(uploaded_file)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            logger.exception("Failed to extract resume text: %s", exc)
            return Response({"detail": "Unable to parse the uploaded resume file."}, status=status.HTTP_400_BAD_REQUEST)

        if not resume_text:
            return Response(
                {
                    "parsed_data": _normalize_parsed_payload({}),
                    "meta": {
                        "used_ai": False,
                        "chars_extracted": 0,
                        "warning": "Could not extract readable text from resume. You can continue and fill details manually.",
                    },
                },
                status=status.HTTP_200_OK,
            )

        ai_payload = None
        try:
            ai_payload = _llm_parse_resume(resume_text)
        except Exception as exc:
            logger.warning("AI resume parse failed, falling back to heuristic parse: %s", exc)

        parsed_payload = _normalize_parsed_payload(ai_payload) if isinstance(ai_payload, dict) else _heuristic_parse_resume(resume_text)
        parsed_payload = _normalize_parsed_payload(parsed_payload)

        return Response(
            {
                "parsed_data": parsed_payload,
                "meta": {
                    "used_ai": isinstance(ai_payload, dict),
                    "chars_extracted": len(resume_text),
                },
            },
            status=status.HTTP_200_OK,
        )


# ============================================================================
# Profile Views
# ============================================================================

class ProfileView(APIView):
    """Main profile endpoint for GET/PUT."""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get current user's profile."""
        serializer = UserProfileSerializer(request.user, context={"request": request})
        return Response(serializer.data)
    
    def put(self, request):
        """Update current user's profile."""
        serializer = UserProfileSerializer(
            request.user, 
            data=request.data, 
            partial=True,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ProfilePictureView(APIView):
    """Handle profile picture upload."""
    
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request):
        """Upload profile picture."""
        serializer = ProfilePictureSerializer(
            request.user,
            data=request.data,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({
            "message": "Profile picture uploaded successfully",
            "picture_url": serializer.data.get("profile_picture_url")
        }, status=status.HTTP_200_OK)


class ProfileCompletenessView(APIView):
    """Get profile completeness score and suggestions."""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get profile completeness details."""
        details = ProfileService.get_completeness_details(request.user)
        serializer = ProfileCompletenessSerializer(details)
        return Response(serializer.data)


# ============================================================================
# Education Views
# ============================================================================

class UserEducationViewSet(viewsets.ModelViewSet):
    """ViewSet for user education CRUD operations."""
    
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return educations for current user."""
        return EducationService.get_user_educations(self.request.user)
    
    def get_serializer_class(self):
        """Return appropriate serializer."""
        if self.action == "list":
            return UserEducationListSerializer
        return UserEducationSerializer


# ============================================================================
# Experience Views
# ============================================================================

class UserExperienceViewSet(viewsets.ModelViewSet):
    """ViewSet for user experience CRUD operations."""
    
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return experiences for current user."""
        return ExperienceService.get_user_experiences(self.request.user)
    
    def get_serializer_class(self):
        """Return appropriate serializer."""
        if self.action == "list":
            return UserExperienceListSerializer
        return UserExperienceSerializer


# ============================================================================
# Certification Views
# ============================================================================

class UserCertificationViewSet(viewsets.ModelViewSet):
    """ViewSet for user certification CRUD operations."""
    
    serializer_class = UserCertificationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return certifications for current user."""
        return UserCertification.objects.filter(user=self.request.user).prefetch_related(
            "related_skills"
        ).order_by("-issue_date")


# ============================================================================
# Project Views
# ============================================================================

class UserProjectViewSet(viewsets.ModelViewSet):
    """ViewSet for user project CRUD operations."""
    
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return projects for current user."""
        status_filter = self.request.query_params.get("status")
        queryset = UserProject.objects.filter(user=self.request.user).prefetch_related(
            "related_skills"
        )
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset.order_by("-is_featured", "-end_date")

    serializer_class = UserProjectSerializer


# ============================================================================
# Language Views
# ============================================================================

class UserLanguageViewSet(viewsets.ModelViewSet):
    """ViewSet for user language CRUD operations."""
    
    serializer_class = UserLanguageSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return languages for current user."""
        return UserLanguage.objects.filter(user=self.request.user)


# ============================================================================
# Social Link Views
# ============================================================================

class UserSocialLinkViewSet(viewsets.ModelViewSet):
    """ViewSet for user social link CRUD operations."""
    
    serializer_class = UserSocialLinkSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return social links for current user."""
        return UserSocialLink.objects.filter(user=self.request.user)


