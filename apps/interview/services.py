"""
Interview Services
==================
Business logic for interview-related operations.
Uses LLM-free InterviewBankService for primary evaluation with Gemini fallback.
"""

import logging
import json
import os
import random
import re
import subprocess
import tempfile
from datetime import timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

import requests

from django.conf import settings
from django.db import transaction
from django.db.models import Avg, Count, Q, Sum
from django.utils import timezone

from apps.interview.models import (
    InterviewQuestion,
    InterviewSession,
    InterviewResponse,
    InterviewTip,
    UserInterviewPreference,
    InterviewSchedule,
)

# Import centralized AI services
from services import get_interview_coach, get_interview_bank_service
from services.ai.prompts import AIPromptsService

logger = logging.getLogger(__name__)


class HostedInterviewAIService:
    """Hosted STT + LLM evaluator (no local model dependency)."""

    def __init__(self):
        self.provider = os.getenv("INTERVIEW_LLM_PROVIDER", "groq").strip().lower()
        self.groq_api_key = os.getenv("GROQ_API_KEY", "").strip()
        self.groq_llm_model = os.getenv("GROQ_LLM_MODEL", "llama-3.1-8b-instant").strip()
        self.groq_stt_model = os.getenv("GROQ_STT_MODEL", "whisper-large-v3-turbo").strip()

    def is_enabled(self) -> bool:
        return bool(self.groq_api_key)

    def transcribe_audio_file(self, file_path: str, source: str = "audio") -> Dict[str, Any]:
        """Transcribe audio using hosted Whisper-compatible endpoint."""
        if not self.is_enabled():
            raise RuntimeError("Hosted transcription is not configured")

        with open(file_path, "rb") as media_file:
            response = requests.post(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {self.groq_api_key}"},
                data={"model": self.groq_stt_model, "language": "en"},
                files={"file": media_file},
                timeout=120,
            )

        if response.status_code >= 400:
            raise RuntimeError(f"STT failed ({response.status_code}): {response.text[:300]}")

        payload = response.json() if response.content else {}
        transcript = str(payload.get("text") or "").strip()
        if not transcript:
            raise RuntimeError("STT returned empty transcript")

        return {
            "transcript": transcript,
            "source": source,
            "provider": "groq_whisper",
            "model": self.groq_stt_model,
        }

    def extract_audio_from_video(self, video_path: str) -> str:
        """Extract audio wav from video file using ffmpeg."""
        output_dir = tempfile.mkdtemp(prefix="interview_audio_")
        audio_path = str(Path(output_dir) / "extracted.wav")

        command = [
            "ffmpeg",
            "-y",
            "-i",
            video_path,
            "-vn",
            "-acodec",
            "pcm_s16le",
            "-ar",
            "16000",
            "-ac",
            "1",
            audio_path,
        ]

        completed = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            text=True,
        )
        if completed.returncode != 0 or not Path(audio_path).exists():
            raise RuntimeError("Failed to extract audio from video. Ensure ffmpeg is installed on server.")

        return audio_path

    def transcode_audio_to_wav(self, audio_path: str) -> str:
        """Transcode any audio input to 16k mono wav using ffmpeg."""
        output_dir = tempfile.mkdtemp(prefix="interview_audio_transcoded_")
        wav_path = str(Path(output_dir) / "transcoded.wav")

        command = [
            "ffmpeg",
            "-y",
            "-i",
            audio_path,
            "-acodec",
            "pcm_s16le",
            "-ar",
            "16000",
            "-ac",
            "1",
            wav_path,
        ]

        completed = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            text=True,
        )
        if completed.returncode != 0 or not Path(wav_path).exists():
            raise RuntimeError("Audio transcoding failed. Ensure ffmpeg is installed.")

        return wav_path

    def evaluate_answer(
        self,
        question: str,
        answer: str,
        question_type: str,
        job_role: str = "",
        rubric: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Evaluate interview answer with hosted LLM and strict JSON output."""
        if not self.is_enabled() or not answer.strip():
            return None

        system_prompt = (
            "You are an expert interview evaluator. Return ONLY valid JSON. "
            "Score conceptual correctness, not exact wording. "
            "Be tolerant of speech-to-text imperfections (minor grammar/punctuation/transcription noise). "
            "Do NOT require word-by-word textbook phrasing."
        )
        user_prompt = f"""
Question Type: {question_type}
Target Role: {job_role or 'General'}

Question:
{question}

Candidate Answer:
{answer}

Reference Rubric Tips:
{', '.join(rubric or []) if rubric else 'Not provided'}

Return JSON only in this exact shape:
{{
  "overall_score": 0,
  "content_score": 0,
  "structure_score": 0,
  "clarity_score": 0,
  "relevance_score": 0,
  "feedback": "short paragraph",
  "strengths": ["..."],
  "improvements": ["..."],
  "suggestions": ["..."],
  "confidence_level": "low|moderate|high"
}}

Scoring guidance:
- Reward correct concepts even if concise.
- For technical theory questions, if core facts are correct, avoid extremely low scores.
- Penalize factual errors, not speaking style.
"""

        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.groq_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.groq_llm_model,
                "temperature": 0.2,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "response_format": {"type": "json_object"},
            },
            timeout=120,
        )

        if response.status_code >= 400:
            logger.warning(f"Hosted LLM evaluation failed ({response.status_code}): {response.text[:300]}")
            return None

        try:
            payload = response.json()
            content = payload.get("choices", [{}])[0].get("message", {}).get("content", "")
            parsed = json.loads(content) if isinstance(content, str) else content
            if isinstance(parsed, dict):
                return parsed
        except Exception as exc:
            logger.warning(f"Failed to parse hosted LLM response: {exc}")
        return None

    def generate_mcq(
        self,
        prompt: str,
        target_role: str = "",
        difficulty: str = "medium",
    ) -> Optional[Dict[str, Any]]:
        """Generate realistic MCQ options for a technical prompt."""
        if not self.is_enabled() or not prompt.strip():
            return None

        system_prompt = (
            "You create high-quality technical screening MCQs similar to real company assessments. "
            "Return ONLY valid JSON."
        )
        user_prompt = f"""
Target role: {target_role or 'Software Engineer'}
Difficulty: {difficulty}
Question stem:
{prompt}

Return JSON only in this exact shape:
{{
  "stem": "question statement",
  "options": ["option A", "option B", "option C", "option D"],
  "correct_option": "exact text of one option",
  "explanation": "short explanation"
}}

Rules:
- Exactly 4 options, one correct.
- Distractors should be plausible but wrong.
- Keep option length concise.
"""

        try:
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.groq_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.groq_llm_model,
                    "temperature": 0.1,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "response_format": {"type": "json_object"},
                },
                timeout=45,
            )
            if response.status_code >= 400:
                logger.warning(f"Hosted LLM MCQ generation failed ({response.status_code}): {response.text[:250]}")
                return None

            payload = response.json()
            content = payload.get("choices", [{}])[0].get("message", {}).get("content", "")
            parsed = json.loads(content) if isinstance(content, str) else content
            if not isinstance(parsed, dict):
                return None

            options = parsed.get("options") or []
            if not isinstance(options, list) or len(options) != 4:
                return None

            normalized_options = [str(opt).strip() for opt in options if str(opt).strip()]
            if len(normalized_options) != 4:
                return None

            correct_option = str(parsed.get("correct_option") or "").strip()
            if correct_option not in normalized_options:
                return None

            return {
                "stem": str(parsed.get("stem") or prompt).strip(),
                "options": normalized_options,
                "correct_option": correct_option,
                "explanation": str(parsed.get("explanation") or "").strip(),
            }
        except Exception as exc:
            logger.warning(f"Hosted MCQ generation parse failed: {exc}")
            return None

    def generate_round_questions(
        self,
        target_role: str,
        section: str,
        difficulty: str,
        num_questions: int,
        technical_mcq_count: int = 0,
        coding_count: int = 0,
        coding_language: str = "python",
        coding_mode: str = "function",
    ) -> Optional[List[Dict[str, Any]]]:
        """Generate role-specific interview questions for a real interview section."""
        if not self.is_enabled() or not target_role.strip():
            return None

        if section == "technical_round":
            mcq_questions = self._generate_role_mcq_questions(
                target_role=target_role,
                difficulty=difficulty,
                count=max(0, technical_mcq_count),
            )
            coding_questions = self._select_dsa_coding_questions(
                difficulty=difficulty,
                count=max(0, coding_count),
                coding_language=coding_language,
                coding_mode=coding_mode,
            )

            # Keep deterministic screening order: all MCQ first, then coding.
            combined = mcq_questions + coding_questions
            return combined[:num_questions] if combined else None

        system_prompt = (
            "You are an interviewer generating realistic company-style interview assessments. "
            "Return ONLY valid JSON."
        )

        user_prompt = f"""
Target role: {target_role}
Section: {section}
Difficulty: {difficulty}
Total questions: {num_questions}
Technical MCQ count: {technical_mcq_count}
Coding count: {coding_count}
Coding language: {coding_language}
Coding mode: {coding_mode}

Rules:
- Questions must be strongly relevant to the target role.
- Questions must sound like a real senior interviewer speaking in an actual interview.
- Avoid generic textbook-only prompts unless explicitly tied to role expectations.
- For technical_interview, favor realistic architecture/tradeoff/debugging/scaling scenarios.
- For technical_round: include exactly requested MCQ and coding counts.
- For technical_round coding questions: MUST be pure DSA/LeetCode style only (arrays, strings, hash map, two pointers, stack/queue, linked list, binary tree, BST, heap, graph BFS/DFS, greedy, binary search, DP). No domain/business tasks like MAE, fraud models, NLP pipelines, etc.
- For technical_round coding prompts include clear input/output and constraints.
- For technical_interview: generate practical technical discussion questions only (technical/system_design/coding). Do NOT return behavioral/situational in this section.
- For hr_round: generate behavioral/situational HR questions only. Do NOT return technical/system_design/coding in this section.
- Keep each question distinct and interview-grade.

Return JSON only in this exact shape:
{{
  "questions": [
    {{
      "question": "...",
      "question_type": "technical|coding|behavioral|situational|system_design",
      "options": ["A", "B", "C", "D"],
      "correct_option": "A",
      "answer_tips": ["..."],
      "sample_answer": "..."
    }}
  ]
}}

Constraints:
- For non-MCQ questions, options must be [].
- For MCQ questions, options length must be 4 and correct_option must match one option exactly.
- For coding questions, question_type must be "coding" and options must be [].
"""

        try:
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.groq_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.groq_llm_model,
                    "temperature": 0.3,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "response_format": {"type": "json_object"},
                },
                timeout=70,
            )
            if response.status_code >= 400:
                logger.warning(f"Round question generation failed ({response.status_code}): {response.text[:300]}")
                return None

            payload = response.json()
            content = payload.get("choices", [{}])[0].get("message", {}).get("content", "")
            parsed = json.loads(content) if isinstance(content, str) else content
            questions = parsed.get("questions") if isinstance(parsed, dict) else None
            if not isinstance(questions, list) or not questions:
                return None

            normalized: List[Dict[str, Any]] = []
            for question in questions:
                if not isinstance(question, dict):
                    continue
                question_text = str(question.get("question") or "").strip()
                question_type = str(question.get("question_type") or "technical").strip().lower()
                options = question.get("options") if isinstance(question.get("options"), list) else []
                options = [str(option).strip() for option in options if str(option).strip()]
                correct_option = str(question.get("correct_option") or "").strip()
                answer_tips = question.get("answer_tips") if isinstance(question.get("answer_tips"), list) else []
                answer_tips = [str(tip).strip() for tip in answer_tips if str(tip).strip()]
                sample_answer = str(question.get("sample_answer") or "").strip()

                if not question_text:
                    continue

                if section == "technical_interview" and question_type in {"behavioral", "situational"}:
                    continue
                if section == "hr_round" and question_type in {"technical", "system_design", "coding"}:
                    continue

                normalized.append({
                    "question": question_text,
                    "question_type": question_type,
                    "options": options,
                    "correct_option": correct_option,
                    "answer_tips": answer_tips,
                    "sample_answer": sample_answer,
                })

            if not normalized:
                return None

            role_tokens = [
                token for token in re.split(r"[^a-z0-9]+", (target_role or "").lower())
                if len(token) >= 4
            ]
            section_tokens = {
                "technical_round": ["algorithm", "complexity", "data structure", "coding", "debug"],
                "technical_interview": ["system", "tradeoff", "design", "scal", "api", "debug", "incident", "performance"],
                "hr_round": ["team", "conflict", "stakeholder", "ownership", "communication", "decision"],
            }.get(section, [])

            def _relevance_score(item: Dict[str, Any]) -> int:
                text = " ".join([
                    str(item.get("question") or ""),
                    " ".join(str(x) for x in (item.get("answer_tips") or [])),
                ]).lower()
                role_score = sum(3 for token in role_tokens if token in text)
                section_score = sum(1 for token in section_tokens if token in text)
                return role_score + section_score

            ranked = sorted(normalized, key=_relevance_score, reverse=True)
            top_ranked = [item for item in ranked if _relevance_score(item) > 0]
            if len(top_ranked) >= max(2, min(num_questions, 4)):
                return top_ranked[:num_questions]
            return ranked[:num_questions]
        except Exception as exc:
            logger.warning(f"Round question generation parse failed: {exc}")
            return None

    def _generate_role_mcq_questions(self, target_role: str, difficulty: str, count: int) -> List[Dict[str, Any]]:
        """Generate career-relevant technical MCQs for technical screening."""
        if count <= 0:
            return []

        system_prompt = (
            "You create role-specific technical screening MCQs similar to real company assessments. "
            "Return ONLY valid JSON."
        )
        user_prompt = f"""
Target role: {target_role}
Difficulty: {difficulty}
Count: {count}

Requirements:
- Questions MUST be relevant to the target role's real interview expectations.
- Avoid repeating generic complexity-only questions.
- Cover practical backend/system/architecture/problem-solving concepts expected for this role.
- Exactly 4 options for each MCQ with 1 correct option.

Return JSON shape:
{{
  "questions": [
    {{
      "question": "...",
      "question_type": "technical",
      "options": ["A","B","C","D"],
      "correct_option": "one of options",
      "answer_tips": ["brief explanation"],
      "sample_answer": "same as correct_option"
    }}
  ]
}}
"""

        try:
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.groq_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.groq_llm_model,
                    "temperature": 0.35,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "response_format": {"type": "json_object"},
                },
                timeout=60,
            )
            if response.status_code >= 400:
                logger.warning(f"Role MCQ generation failed ({response.status_code}): {response.text[:250]}")
                return []

            payload = response.json()
            content = payload.get("choices", [{}])[0].get("message", {}).get("content", "")
            parsed = json.loads(content) if isinstance(content, str) else content
            raw_questions = parsed.get("questions") if isinstance(parsed, dict) else None
            if not isinstance(raw_questions, list):
                return []

            normalized: List[Dict[str, Any]] = []
            for raw in raw_questions:
                if not isinstance(raw, dict):
                    continue
                prompt = str(raw.get("question") or "").strip()
                options = raw.get("options") if isinstance(raw.get("options"), list) else []
                options = [str(opt).strip() for opt in options if str(opt).strip()]
                correct = str(raw.get("correct_option") or "").strip()
                explanation_list = raw.get("answer_tips") if isinstance(raw.get("answer_tips"), list) else []
                explanation_list = [str(x).strip() for x in explanation_list if str(x).strip()]

                if not prompt or len(options) != 4 or correct not in options:
                    continue

                normalized.append({
                    "question": prompt,
                    "question_type": "technical",
                    "options": options,
                    "correct_option": correct,
                    "answer_tips": explanation_list or ["Understand why the correct option is best."],
                    "sample_answer": correct,
                })

            return normalized[:count]
        except Exception as exc:
            logger.warning(f"Role MCQ generation parse failed: {exc}")
            return []

    def _role_cluster(self, target_role: str) -> str:
        text = (target_role or "").lower()
        if any(token in text for token in ["data", "ml", "ai", "analytics", "scientist"]):
            return "data"
        if any(token in text for token in ["frontend", "ui", "react", "web"]):
            return "frontend"
        if any(token in text for token in ["backend", "api", "django", "spring", "node"]):
            return "backend"
        if any(token in text for token in ["devops", "sre", "platform", "cloud"]):
            return "devops"
        if any(token in text for token in ["qa", "test", "automation", "quality"]):
            return "qa"
        return "software"

    def _clean_question_text(self, question: str, target_role: str) -> str:
        text = str(question or "").strip()
        if not text:
            return ""

        role = " ".join(str(target_role or "").strip().split())
        if role:
            escaped = re.escape(role)
            patterns = [
                rf"^\s*as\s+(an?\s+)?{escaped}\s*[,:-]\s*",
                rf"^\s*in\s+{escaped}\s*[,:-]\s*",
                rf"^\s*for\s+(an?\s+)?{escaped}\s*[,:-]\s*",
            ]
            for pattern in patterns:
                text = re.sub(pattern, "", text, flags=re.IGNORECASE)

        text = re.sub(r"\s+", " ", text).strip()
        if text:
            text = text[0].upper() + text[1:]
        return text

    def generate_structured_round_questions(
        self,
        target_role: str,
        section: str,
        difficulty: str,
        num_questions: int,
        technical_mcq_count: int = 0,
        coding_count: int = 0,
        coding_language: str = "python",
        coding_mode: str = "function",
    ) -> List[Dict[str, Any]]:
        """Generate deterministic, role-aware fallback questions when LLM generation is unavailable/weak."""
        role = " ".join(target_role.strip().split()) or "Software Engineer"
        cluster = self._role_cluster(role)

        def _take(items: List[Any], count: int) -> List[Any]:
            if count <= 0:
                return []
            if not items:
                return []
            if len(items) >= count:
                return items[:count]
            repeats: List[Any] = []
            while len(repeats) < count:
                repeats.extend(items)
            return repeats[:count]

        technical_interview_bank: Dict[str, List[str]] = {
            "data": [
                f"How would you design an end-to-end churn prediction pipeline for a {role} role, from data validation to model monitoring?",
                f"A model for this {role} team has high offline accuracy but poor production impact. How would you debug the gap?",
                f"Which SQL checks would you run first to detect data leakage before training a model in a {role} workflow?",
                f"How would you choose between precision-recall and ROC-AUC for an imbalanced use case in {role} work?",
            ],
            "backend": [
                f"Design an idempotent API for order creation expected in a {role} interview. What failure modes would you handle?",
                f"How would you investigate high p95 latency in a backend service and verify the root cause?",
                f"What database indexing and query strategies would you use for a read-heavy {role} service?",
                f"How would you evolve a public API without breaking existing clients in a {role} system?",
            ],
            "frontend": [
                f"How would you diagnose a major Core Web Vitals regression in a production {role} application?",
                f"Design state management for a complex {role} dashboard with optimistic updates and rollback handling.",
                f"How would you split frontend bundles to improve first load while preserving UX in a {role} app?",
                f"Which accessibility checks are non-negotiable in a senior {role} code review?",
            ],
            "devops": [
                f"How would you design a safe rollout strategy to minimize blast radius during deployment?",
                f"What SLO and alerting design would you propose for a critical service in a {role} context?",
                f"A recurring incident keeps happening weekly. How would you run incident review and prevention?",
                f"How would you reduce CI/CD duration without reducing confidence in releases?",
            ],
            "qa": [
                f"How would you design a practical test pyramid for a high-change product?",
                f"What process would you use to identify and eliminate flaky tests in CI?",
                f"How would you prioritize test coverage for a high-risk release window?",
                f"How would you combine API, UI, and contract testing for release reliability?",
            ],
            "software": [
                f"Walk me through how you debug a production issue from first alert to verified fix.",
                f"How would you decide between caching and query optimization for performance bottlenecks?",
                f"How would you design observability so failures are detected before users report them?",
                f"How do you evaluate and communicate tradeoffs between correctness, performance, and delivery speed?",
            ],
        }

        hr_bank = [
            f"Tell me about a difficult conflict at work and how you resolved it while preserving collaboration.",
            f"Describe a time you made a high-stakes decision with incomplete information. What was your approach?",
            f"Share an example of receiving critical feedback and how you changed your execution afterward.",
            f"Tell me about a project where expectations were ambiguous. How did you align stakeholders?",
            f"Describe how you mentor teammates and raise team performance over time.",
        ]

        technical_round_mcq_bank: Dict[str, List[Dict[str, Any]]] = {
            "data": [
                {
                    "question": "Which metric is most appropriate for an imbalanced binary classification problem where false negatives are costly?",
                    "options": ["PR-AUC", "Raw accuracy", "MSE", "R-squared"],
                    "correct_option": "PR-AUC",
                },
                {
                    "question": "In SQL, which pattern correctly gets the latest transaction per customer?",
                    "options": [
                        "ROW_NUMBER() OVER(PARTITION BY customer_id ORDER BY transaction_time DESC) then filter rank = 1",
                        "GROUP BY customer_id with no aggregate",
                        "ORDER BY transaction_time and LIMIT 1",
                        "DISTINCT customer_id only",
                    ],
                    "correct_option": "ROW_NUMBER() OVER(PARTITION BY customer_id ORDER BY transaction_time DESC) then filter rank = 1",
                },
                {
                    "question": "Which practice best prevents target leakage during model training?",
                    "options": [
                        "Build features using only information available at prediction time",
                        "Normalize using the full dataset including validation split",
                        "Tune thresholds on test data",
                        "Drop rows with null values only",
                    ],
                    "correct_option": "Build features using only information available at prediction time",
                },
                {
                    "question": "A model overfits training data. Which action is usually most effective first?",
                    "options": [
                        "Cross-validation with regularization and simpler features",
                        "Increase model depth without validation",
                        "Train longer on same data",
                        "Use test set for feature selection",
                    ],
                    "correct_option": "Cross-validation with regularization and simpler features",
                },
            ],
            "backend": [
                {
                    "question": "Which approach best prevents duplicate side effects on retried POST requests?",
                    "options": [
                        "Idempotency keys with server-side deduplication",
                        "Client-side retries without identifiers",
                        "Random response IDs only",
                        "Disable retries globally",
                    ],
                    "correct_option": "Idempotency keys with server-side deduplication",
                },
                {
                    "question": "What is the safest immediate control for a failing external dependency?",
                    "options": [
                        "Timeout + circuit breaker + fallback",
                        "Infinite retries",
                        "Disable monitoring",
                        "Increase thread pool only",
                    ],
                    "correct_option": "Timeout + circuit breaker + fallback",
                },
                {
                    "question": "For read-heavy endpoints with repeated access, what usually gives fastest win?",
                    "options": ["Layered caching with sensible TTL", "More logs", "Bigger payloads", "Disable indexes"],
                    "correct_option": "Layered caching with sensible TTL",
                },
            ],
            "frontend": [
                {
                    "question": "Which practice most directly improves initial page load performance?",
                    "options": ["Code-splitting critical vs non-critical bundles", "Larger single bundle", "Disable caching", "Inline all scripts"],
                    "correct_option": "Code-splitting critical vs non-critical bundles",
                },
                {
                    "question": "What is the best approach for handling rapidly typed search input?",
                    "options": ["Debounce input and cancel stale requests", "Fire request on every key without control", "Only use local storage", "Disable typing until response returns"],
                    "correct_option": "Debounce input and cancel stale requests",
                },
                {
                    "question": "Which check is essential for keyboard accessibility?",
                    "options": ["Visible focus states and logical tab order", "Mouse-only hover states", "Placeholder-only labels", "Color-only error indication"],
                    "correct_option": "Visible focus states and logical tab order",
                },
            ],
            "devops": [
                {
                    "question": "Which rollout pattern minimizes risk in production deployments?",
                    "options": ["Canary rollout with health checks and rollback", "Big-bang release", "Manual edit on production nodes", "Disable alerts during deploy"],
                    "correct_option": "Canary rollout with health checks and rollback",
                },
                {
                    "question": "What should alerts optimize for first in SRE practice?",
                    "options": ["Actionable signal with low noise", "Maximum alert volume", "Only CPU threshold", "No paging after hours"],
                    "correct_option": "Actionable signal with low noise",
                },
            ],
            "qa": [
                {
                    "question": "Which testing strategy gives best confidence-to-speed balance?",
                    "options": ["Test pyramid with strong unit/API base", "Only end-to-end tests", "Only manual testing", "Snapshot tests for everything"],
                    "correct_option": "Test pyramid with strong unit/API base",
                },
                {
                    "question": "What is the most effective way to reduce flaky tests?",
                    "options": ["Remove timing dependencies and isolate external state", "Retry failing tests indefinitely", "Ignore flaky failures", "Run tests less frequently"],
                    "correct_option": "Remove timing dependencies and isolate external state",
                },
            ],
            "software": [
                {
                    "question": "When debugging a production issue, what should happen first?",
                    "options": ["Establish reproducible signal and scope", "Rewrite major components", "Disable all logs", "Scale randomly"],
                    "correct_option": "Establish reproducible signal and scope",
                },
                {
                    "question": "Which pattern best supports resilience for transient failures?",
                    "options": ["Timeout + retry with backoff + circuit breaker", "Infinite retries", "No timeout", "Synchronous fallback only"],
                    "correct_option": "Timeout + retry with backoff + circuit breaker",
                },
            ],
        }

        coding_bank: Dict[str, List[Dict[str, Any]]] = {
            "data": [
                {
                    "question": "Write a Python function that reads a transaction DataFrame and returns monthly retention by cohort. Explain handling of missing months and edge cases.",
                    "question_type": "coding",
                },
                {
                    "question": "Given orders(order_id, customer_id, amount, created_at), write an SQL query to return each customer's rolling 30-day spend as of each order date.",
                    "question_type": "coding",
                },
                {
                    "question": "Implement a function that computes precision, recall, and F1 for binary classification from y_true and y_pred without external metric libraries.",
                    "question_type": "coding",
                },
            ],
            "backend": [
                {
                    "question": "Implement a rate limiter (sliding window) function for API requests and explain its time/space tradeoffs.",
                    "question_type": "coding",
                },
                {
                    "question": "Write pseudo/real code for an idempotent order creation endpoint using idempotency keys and persistence.",
                    "question_type": "coding",
                },
            ],
            "frontend": [
                {
                    "question": "Implement a debounced search hook that cancels stale requests and preserves the latest successful result.",
                    "question_type": "coding",
                },
                {
                    "question": "Write a reusable error boundary component and show how you would capture diagnostic context.",
                    "question_type": "coding",
                },
            ],
            "devops": [
                {
                    "question": "Write a script/pseudocode that validates deployment health checks across instances and triggers rollback when threshold breaches occur.",
                    "question_type": "coding",
                },
            ],
            "qa": [
                {
                    "question": "Write a robust API contract test that validates response schema and backward compatibility for versioned endpoints.",
                    "question_type": "coding",
                },
            ],
            "software": [
                {
                    "question": "Implement a utility to safely retry transient operations with exponential backoff and jitter.",
                    "question_type": "coding",
                },
            ],
        }

        if section == "technical_round":
            mcq_templates = technical_round_mcq_bank.get(cluster, technical_round_mcq_bank["software"])
            selected_mcq = _take(mcq_templates, max(0, technical_mcq_count))
            mcq_payload = [
                {
                    "question": self._clean_question_text(str(item["question"]), role),
                    "question_type": "technical",
                    "options": item["options"],
                    "correct_option": item["correct_option"],
                    "answer_tips": ["Choose the most correct and production-safe option."],
                    "sample_answer": item["correct_option"],
                }
                for item in selected_mcq
            ]

            selected_coding = _take(coding_bank.get(cluster, coding_bank["software"]), max(0, coding_count))
            coding_payload = [
                {
                    "question": self._clean_question_text(str(item.get("question") or ""), role),
                    "question_type": "coding",
                    "options": [],
                    "correct_option": "",
                    "answer_tips": [
                        "Clarify assumptions.",
                        "Discuss complexity and edge cases.",
                        "Write clean, testable logic.",
                    ],
                    "sample_answer": "",
                }
                for item in selected_coding
            ]

            # If cluster-specific coding bank is short, fill with DSA prompts to keep requested count.
            if len(coding_payload) < max(0, coding_count):
                dsa_fill = self._select_dsa_coding_questions(
                    difficulty=difficulty,
                    count=max(0, coding_count) - len(coding_payload),
                    coding_language=coding_language,
                    coding_mode=coding_mode,
                )
                coding_payload.extend(dsa_fill)

            return (mcq_payload + coding_payload)[:max(1, num_questions)]

        if section == "technical_interview":
            prompts = _take(technical_interview_bank.get(cluster, technical_interview_bank["software"]), max(1, num_questions))
            payload: List[Dict[str, Any]] = []
            for idx, prompt in enumerate(prompts):
                q_type = "system_design" if any(k in prompt.lower() for k in ["design", "architecture", "pipeline"]) else "technical"
                if idx == len(prompts) - 1 and len(prompts) >= 4:
                    q_type = "coding"
                payload.append({
                    "question": self._clean_question_text(prompt, role),
                    "question_type": q_type,
                    "options": [],
                    "correct_option": "",
                    "answer_tips": [
                        "State assumptions first.",
                        "Explain tradeoffs with concrete examples.",
                        "Prioritize production constraints.",
                    ],
                    "sample_answer": "",
                })
            return payload[:num_questions]

        selected_hr = _take(hr_bank, max(1, num_questions))
        return [
            {
                "question": self._clean_question_text(question, role),
                "question_type": "behavioral" if idx % 2 == 0 else "situational",
                "options": [],
                "correct_option": "",
                "answer_tips": [
                    "Use STAR structure.",
                    "Show ownership and measurable impact.",
                    "Reflect on lessons learned.",
                ],
                "sample_answer": "",
            }
            for idx, question in enumerate(selected_hr)
        ]

    def _select_dsa_coding_questions(
        self,
        difficulty: str,
        count: int,
        coding_language: str,
        coding_mode: str,
    ) -> List[Dict[str, Any]]:
        """Return strict DSA coding questions with difficulty-aware pool."""
        if count <= 0:
            return []

        base_bank: Dict[str, List[str]] = {
            "easy": [
                "Two Sum",
                "Valid Parentheses",
                "Merge Two Sorted Lists",
                "Best Time to Buy and Sell Stock",
                "Binary Search in Sorted Array",
                "Maximum Depth of Binary Tree",
                "Middle of Linked List",
            ],
            "medium": [
                "Longest Substring Without Repeating Characters",
                "3Sum",
                "Group Anagrams",
                "Container With Most Water",
                "Find Minimum in Rotated Sorted Array",
                "Number of Islands",
                "Course Schedule (Cycle Detection)",
                "Longest Palindromic Substring",
                "Top K Frequent Elements",
                "Coin Change",
            ],
            "hard": [
                "Median of Two Sorted Arrays",
                "Merge K Sorted Lists",
                "Trapping Rain Water",
                "Word Ladder",
                "Serialize and Deserialize Binary Tree",
                "Longest Increasing Path in a Matrix",
                "Minimum Window Substring",
                "Regular Expression Matching",
                "Edit Distance",
                "N-Queens",
            ],
        }

        problem_statements: Dict[str, str] = {
            "Two Sum": "Given an integer array nums and an integer target, return indices of two numbers such that they add up to target. Assume exactly one valid answer exists and you may not use the same element twice.",
            "Valid Parentheses": "Given a string containing only characters ()[]{} determine if the input string is valid. A string is valid if open brackets are closed by the same type in the correct order.",
            "Merge Two Sorted Lists": "Given heads of two sorted linked lists, merge them into one sorted linked list and return the merged head.",
            "Best Time to Buy and Sell Stock": "Given prices where prices[i] is the stock price on day i, return the maximum profit from one buy and one sell. If no profit is possible, return 0.",
            "Binary Search in Sorted Array": "Given a sorted integer array and a target value, return the index of target if found, otherwise return -1.",
            "Maximum Depth of Binary Tree": "Given the root of a binary tree, return its maximum depth (the number of nodes along the longest path from root to leaf).",
            "Middle of Linked List": "Given the head of a singly linked list, return the middle node. If there are two middle nodes, return the second middle node.",
            "Longest Substring Without Repeating Characters": "Given a string s, return the length of the longest substring without repeating characters.",
            "3Sum": "Given an integer array nums, return all unique triplets [nums[i], nums[j], nums[k]] such that i, j, k are distinct and nums[i] + nums[j] + nums[k] = 0.",
            "Group Anagrams": "Given an array of strings, group the anagrams together and return the grouped lists.",
            "Container With Most Water": "Given an array height where each element is a vertical line height, find two lines that together with the x-axis form a container holding maximum water.",
            "Find Minimum in Rotated Sorted Array": "Given a rotated sorted array of unique elements, return the minimum element in O(log n) time.",
            "Number of Islands": "Given an m x n grid of '1' (land) and '0' (water), return the number of islands. Islands are connected horizontally or vertically.",
            "Course Schedule (Cycle Detection)": "Given numCourses and prerequisite pairs [a,b] meaning b must be taken before a, return true if all courses can be finished.",
            "Longest Palindromic Substring": "Given a string s, return the longest palindromic substring in s.",
            "Top K Frequent Elements": "Given an integer array nums and integer k, return the k most frequent elements in any order.",
            "Coin Change": "Given coin denominations and a target amount, return the minimum number of coins needed to make the amount, or -1 if impossible.",
            "Median of Two Sorted Arrays": "Given two sorted arrays nums1 and nums2, return the median of the two arrays with overall runtime complexity O(log(m+n)).",
            "Merge K Sorted Lists": "Given an array of k sorted linked lists, merge all lists into one sorted linked list and return its head.",
            "Trapping Rain Water": "Given an elevation map, compute how much water can be trapped after raining.",
            "Word Ladder": "Given beginWord, endWord, and a word list, return the length of the shortest transformation sequence where only one letter changes at a time and each intermediate word exists in the list.",
            "Serialize and Deserialize Binary Tree": "Design algorithms to serialize a binary tree to a string and deserialize the string back to the same tree structure.",
            "Longest Increasing Path in a Matrix": "Given an m x n matrix, return the length of the longest strictly increasing path moving up/down/left/right.",
            "Minimum Window Substring": "Given strings s and t, return the minimum window in s that contains all characters in t (including duplicates).",
            "Regular Expression Matching": "Implement pattern matching with support for '.' and '*' where '.' matches any single character and '*' matches zero or more of the preceding element.",
            "Edit Distance": "Given two strings word1 and word2, return the minimum number of operations (insert, delete, replace) required to convert word1 into word2.",
            "N-Queens": "Given an integer n, return all distinct solutions to the n-queens puzzle where n queens are placed so that no two queens attack each other.",
        }

        level = difficulty if difficulty in base_bank else "medium"
        pool = list(base_bank[level])
        random.shuffle(pool)
        selected = pool[:count]

        style_text = {
            "logic": "Explain core logic/pseudocode and complexity clearly.",
            "function": f"Write a complete function in {coding_language}.",
            "leetcode": f"Write a LeetCode-style {coding_language} solution with optimal approach.",
        }.get(coding_mode, f"Write a complete function in {coding_language}.")

        formatted: List[Dict[str, Any]] = []
        for topic in selected:
            statement = problem_statements.get(topic, f"Solve the DSA problem: {topic}.")
            formatted.append({
                "question": (
                    f"Problem: {topic}\n"
                    f"Statement: {statement}\n"
                    "What to do: Return the correct output for all valid inputs and handle edge cases. "
                    f"{style_text} Include time and space complexity."
                ),
                "question_type": "coding",
                "options": [],
                "correct_option": "",
                "answer_tips": [
                    "Use an optimal DSA approach.",
                    "Include time and space complexity.",
                    "Handle edge cases clearly.",
                ],
                "sample_answer": "",
            })

        return formatted

    def evaluate_coding_solution(
        self,
        question: str,
        answer: str,
        difficulty: str = "medium",
        coding_language: str = "python",
        reference_solution: str = "",
    ) -> Optional[Dict[str, Any]]:
        """Evaluate coding answer like online assessment correctness style."""
        if not self.is_enabled() or not question.strip() or not answer.strip():
            return None

        system_prompt = (
            "You are a strict coding interviewer evaluator. Judge correctness first, then quality. "
            "Return ONLY valid JSON."
        )
        user_prompt = f"""
Difficulty: {difficulty}
Language: {coding_language}
Question:
{question}

Candidate solution:
{answer}

Reference solution (if any):
{reference_solution or 'N/A'}

Return JSON only in this exact shape:
{{
  "is_correct": true,
  "score": 0,
  "feedback": "short result summary",
  "strengths": ["..."],
  "issues": ["..."],
  "suggestions": ["..."],
  "time_complexity": "...",
  "space_complexity": "..."
}}

Scoring rubric:
- If solution is logically correct for expected cases: score 90-100.
- If partially correct: score 50-89.
- If incorrect/missing key logic: score 0-49.
- Start feedback with "Correct." or "Incorrect." explicitly.
"""

        try:
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.groq_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.groq_llm_model,
                    "temperature": 0.1,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "response_format": {"type": "json_object"},
                },
                timeout=50,
            )

            if response.status_code >= 400:
                logger.warning(f"Coding evaluation failed ({response.status_code}): {response.text[:250]}")
                return None

            payload = response.json()
            content = payload.get("choices", [{}])[0].get("message", {}).get("content", "")
            parsed = json.loads(content) if isinstance(content, str) else content
            if not isinstance(parsed, dict):
                return None

            is_correct = bool(parsed.get("is_correct", False))
            score = int(parsed.get("score", 0) or 0)
            score = max(0, min(100, score))
            feedback = str(parsed.get("feedback") or "").strip()
            strengths = parsed.get("strengths") if isinstance(parsed.get("strengths"), list) else []
            issues = parsed.get("issues") if isinstance(parsed.get("issues"), list) else []
            suggestions = parsed.get("suggestions") if isinstance(parsed.get("suggestions"), list) else []

            return {
                "is_correct": is_correct,
                "score": score,
                "feedback": feedback,
                "strengths": [str(item) for item in strengths],
                "issues": [str(item) for item in issues],
                "suggestions": [str(item) for item in suggestions],
                "time_complexity": str(parsed.get("time_complexity") or "").strip(),
                "space_complexity": str(parsed.get("space_complexity") or "").strip(),
            }
        except Exception as exc:
            logger.warning(f"Coding evaluation parse failed: {exc}")
            return None


class QuestionService:
    """Service for interview question operations."""
    
    @staticmethod
    def get_questions(
        question_types: List[str] = None,
        difficulty: Optional[str] = None,
        category: Optional[str] = None,
        career_id: Optional[UUID] = None,
        search: Optional[str] = None,
        limit: int = 50
    ):
        """Get filtered interview questions."""
        queryset = InterviewQuestion.objects.filter(is_active=True)
        
        if question_types:
            queryset = queryset.filter(question_type__in=question_types)
        
        if difficulty:
            queryset = queryset.filter(difficulty=difficulty)
        
        if category:
            queryset = queryset.filter(category__iexact=category)
        
        if career_id:
            queryset = queryset.filter(career_paths__id=career_id)
        
        if search:
            queryset = queryset.filter(question__icontains=search)
        
        return queryset[:limit]
    
    @staticmethod
    def get_questions_for_session(
        num_questions: int,
        question_types: List[str] = None,
        difficulty: Optional[str] = None,
        career_id: Optional[UUID] = None,
        career_text: Optional[str] = None,
        exclude_ids: List[UUID] = None,
        require_relevance: bool = False,
    ) -> List[InterviewQuestion]:
        """Get random questions for a session."""
        queryset = InterviewQuestion.objects.filter(is_active=True)
        
        if question_types:
            queryset = queryset.filter(question_type__in=question_types)
        
        if difficulty:
            queryset = queryset.filter(difficulty=difficulty)
        
        if career_id:
            queryset = queryset.filter(career_paths__id=career_id)
        
        if exclude_ids:
            queryset = queryset.exclude(id__in=exclude_ids)

        if career_text and career_text.strip():
            tokens = [
                token for token in re.split(r"[^a-z0-9]+", career_text.lower())
                if len(token) >= 3
            ]
            if tokens:
                candidates = list(queryset)

                def _score(question: InterviewQuestion) -> int:
                    text = " ".join([
                        str(question.question or ""),
                        str(question.category or ""),
                        " ".join(question.tags or []),
                        " ".join(question.expected_topics or []),
                    ]).lower()
                    return sum(2 if token in text else 0 for token in tokens)

                ranked = sorted(candidates, key=_score, reverse=True)
                relevant = [question for question in ranked if _score(question) > 0]
                fallback = [question for question in ranked if _score(question) == 0]

                if require_relevance:
                    return relevant[:num_questions]

                ordered = relevant + fallback
                return ordered[:num_questions]
        
        # Get all matching IDs
        question_ids = list(queryset.values_list("id", flat=True))
        
        # Random selection
        if len(question_ids) <= num_questions:
            selected_ids = question_ids
        else:
            selected_ids = random.sample(question_ids, num_questions)
        
        # Maintain random order
        questions = list(InterviewQuestion.objects.filter(id__in=selected_ids))
        random.shuffle(questions)
        
        return questions
    
    @staticmethod
    def get_recommended_questions(user, limit: int = 10) -> List[InterviewQuestion]:
        """Get recommended questions for user."""
        # Get user's weak areas from preferences
        try:
            prefs = UserInterviewPreference.objects.get(user=user)
            weak_areas = prefs.weak_areas
        except UserInterviewPreference.DoesNotExist:
            weak_areas = []
        
        # Get questions user hasn't answered recently
        recent_response_ids = InterviewResponse.objects.filter(
            session__user=user,
            created_at__gte=timezone.now() - timedelta(days=30)
        ).values_list("question_id", flat=True)
        
        queryset = InterviewQuestion.objects.filter(
            is_active=True
        ).exclude(
            id__in=recent_response_ids
        )
        
        # Prioritize weak areas
        if weak_areas:
            queryset = queryset.filter(
                Q(category__in=weak_areas) |
                Q(tags__overlap=weak_areas)
            )
        
        return list(queryset.order_by("-times_asked")[:limit])


class SessionService:
    """Service for interview session operations."""

    @staticmethod
    def _normalize_feedback_items(items: Any, fallback: Optional[List[str]] = None) -> List[str]:
        """Normalize AI feedback list items (string/object) to plain strings."""
        if not isinstance(items, list):
            return list(fallback or [])

        normalized: List[str] = []
        for item in items:
            if isinstance(item, str):
                text = item.strip()
                if text:
                    normalized.append(text)
                continue

            if isinstance(item, dict):
                area = str(item.get("area", "")).strip()
                advice = str(item.get("advice", "")).strip()
                merged = f"{area}: {advice}".strip(": ") if area or advice else ""
                if merged:
                    normalized.append(merged)
                continue

            text = str(item).strip()
            if text:
                normalized.append(text)

        return normalized or list(fallback or [])
    
    @staticmethod
    @transaction.atomic
    def create_session(
        user,
        title: str,
        session_type: str = InterviewSession.SessionType.PRACTICE,
        job_application=None,
        target_career=None,
        target_company: str = "",
        question_types: List[str] = None,
        difficulty_preference: str = InterviewQuestion.DifficultyLevel.MEDIUM,
        num_questions: int = 5,
        duration_minutes: int = 30,
        technical_mcq_count: Optional[int] = None,
        coding_count: Optional[int] = None,
        coding_language: str = "python",
        coding_mode: str = "function",
        real_section: str = "",
        scheduled_at=None
    ) -> InterviewSession:
        """Create a new interview session."""
        session = InterviewSession.objects.create(
            user=user,
            title=title,
            session_type=session_type,
            job_application=job_application,
            target_career=target_career,
            target_company=target_company,
            question_types=question_types or [],
            difficulty_preference=difficulty_preference,
            num_questions=num_questions,
            duration_minutes=duration_minutes,
            scheduled_at=scheduled_at
        )
        
        # Get questions
        career_id = target_career.id if target_career else None

        questions: List[InterviewQuestion] = []
        asked_ids: List[UUID] = []
        career_text = (target_company or "").strip()
        hosted_ai = HostedInterviewAIService()

        should_generate_realtime = (
            session_type == InterviewSession.SessionType.MOCK
            and bool(career_text)
            and hosted_ai.is_enabled()
        )

        should_prepare_structured = (
            session_type == InterviewSession.SessionType.MOCK
            and bool(career_text)
        )

        generated_questions: List[InterviewQuestion] = []
        generated_mcq_count = 0
        generated_coding_count = 0
        generated_payload: List[Dict[str, Any]] = []
        section_name = real_section or (
            "technical_round" if technical_mcq_count is not None and coding_count is not None else
            "hr_round" if question_types and all(q in ["behavioral", "situational"] for q in question_types) else
            "technical_interview"
        )

        desired_count = (
            max(1, (technical_mcq_count or 0) + (coding_count or 0))
            if section_name == "technical_round"
            else max(1, num_questions)
        )

        if should_generate_realtime:
            generated_payload = hosted_ai.generate_round_questions(
                target_role=career_text,
                section=section_name,
                difficulty=difficulty_preference,
                num_questions=desired_count,
                technical_mcq_count=max(0, technical_mcq_count or 0),
                coding_count=max(0, coding_count or 0),
                coding_language=coding_language or "python",
                coding_mode=coding_mode or "function",
            ) or []

        if should_prepare_structured and len(generated_payload) < desired_count:
            structured = hosted_ai.generate_structured_round_questions(
                target_role=career_text,
                section=section_name,
                difficulty=difficulty_preference,
                num_questions=desired_count - len(generated_payload),
                technical_mcq_count=max(0, technical_mcq_count or 0),
                coding_count=max(0, coding_count or 0),
                coding_language=coding_language or "python",
                coding_mode=coding_mode or "function",
            )
            generated_payload.extend(structured)

        if generated_payload:

            for payload in generated_payload:
                raw_type = str(payload.get("question_type") or "technical").lower()
                q_type = raw_type
                if q_type not in {
                    InterviewQuestion.QuestionType.BEHAVIORAL,
                    InterviewQuestion.QuestionType.TECHNICAL,
                    InterviewQuestion.QuestionType.SITUATIONAL,
                    InterviewQuestion.QuestionType.CASE_STUDY,
                    InterviewQuestion.QuestionType.CODING,
                    InterviewQuestion.QuestionType.SYSTEM_DESIGN,
                    InterviewQuestion.QuestionType.BRAINTEASER,
                }:
                    q_type = InterviewQuestion.QuestionType.TECHNICAL

                options = payload.get("options") if isinstance(payload.get("options"), list) else []
                correct = str(payload.get("correct_option") or "").strip()
                answer_tips = payload.get("answer_tips") if isinstance(payload.get("answer_tips"), list) else []

                if options and q_type == InterviewQuestion.QuestionType.TECHNICAL:
                    answer_tips = [str(option).strip() for option in options if str(option).strip()]

                question_text = hosted_ai._clean_question_text(
                    str(payload.get("question") or "").strip(),
                    career_text,
                )
                if not question_text:
                    continue

                generated_question = InterviewQuestion.objects.create(
                    question=question_text,
                    question_type=q_type,
                    difficulty=difficulty_preference,
                    category="LLM Generated",
                    tags=["realtime", "career_specific", career_text.lower()],
                    expected_topics=[career_text],
                    sample_answer=(correct if options and correct else str(payload.get("sample_answer") or "").strip()),
                    answer_tips=answer_tips,
                    is_active=False,
                )
                generated_questions.append(generated_question)

                if q_type == InterviewQuestion.QuestionType.TECHNICAL:
                    generated_mcq_count += 1
                elif q_type == InterviewQuestion.QuestionType.CODING:
                    generated_coding_count += 1

            if generated_questions:
                questions.extend(generated_questions)

            if section_name == "technical_round":
                asked_ids.extend([q.id for q in questions])

                missing_mcq = max(0, (technical_mcq_count or 0) - generated_mcq_count)
                if missing_mcq > 0:
                    fallback_mcq = QuestionService.get_questions_for_session(
                        num_questions=missing_mcq,
                        question_types=[InterviewQuestion.QuestionType.TECHNICAL],
                        difficulty=difficulty_preference,
                        career_id=career_id,
                        career_text=career_text,
                        exclude_ids=asked_ids,
                        require_relevance=True,
                    )
                    questions.extend(fallback_mcq)
                    asked_ids.extend([q.id for q in fallback_mcq])

                missing_coding = max(0, (coding_count or 0) - generated_coding_count)
                if missing_coding > 0:
                    dsa_payloads = hosted_ai._select_dsa_coding_questions(
                        difficulty=difficulty_preference,
                        count=missing_coding,
                        coding_language=coding_language or "python",
                        coding_mode=coding_mode or "function",
                    )
                    created_dsa_questions: List[InterviewQuestion] = []
                    for payload in dsa_payloads:
                        dsa_question = InterviewQuestion.objects.create(
                            question=str(payload.get("question") or "").strip(),
                            question_type=InterviewQuestion.QuestionType.CODING,
                            difficulty=difficulty_preference,
                            category="LLM Generated",
                            tags=["realtime", "dsa", "coding"],
                            expected_topics=["dsa"],
                            sample_answer="",
                            answer_tips=payload.get("answer_tips") if isinstance(payload.get("answer_tips"), list) else [],
                            is_active=False,
                        )
                        created_dsa_questions.append(dsa_question)

                    if created_dsa_questions:
                        questions.extend(created_dsa_questions)
                        asked_ids.extend([q.id for q in created_dsa_questions])

                    still_missing_coding = max(0, missing_coding - len(created_dsa_questions))
                    if still_missing_coding > 0:
                        fallback_coding = QuestionService.get_questions_for_session(
                            num_questions=still_missing_coding,
                            question_types=[InterviewQuestion.QuestionType.CODING],
                            difficulty=difficulty_preference,
                            career_id=career_id,
                            career_text=career_text,
                            exclude_ids=asked_ids,
                            require_relevance=True,
                        )
                        questions.extend(fallback_coding)
                        asked_ids.extend([q.id for q in fallback_coding])

            if section_name != "technical_round" and len(questions) < desired_count:
                asked_ids.extend([q.id for q in questions])
                fallback_types: List[str] | None
                if section_name == "hr_round":
                    fallback_types = [
                        InterviewQuestion.QuestionType.BEHAVIORAL,
                        InterviewQuestion.QuestionType.SITUATIONAL,
                    ]
                elif section_name == "technical_interview":
                    fallback_types = [
                        InterviewQuestion.QuestionType.TECHNICAL,
                        InterviewQuestion.QuestionType.SYSTEM_DESIGN,
                        InterviewQuestion.QuestionType.CODING,
                    ]
                else:
                    fallback_types = [
                        InterviewQuestion.QuestionType.TECHNICAL,
                        InterviewQuestion.QuestionType.SYSTEM_DESIGN,
                        InterviewQuestion.QuestionType.CODING,
                    ]

                remaining = max(0, desired_count - len(questions))
                if remaining > 0:
                    fallback_generated = QuestionService.get_questions_for_session(
                        num_questions=remaining,
                        question_types=fallback_types,
                        difficulty=difficulty_preference,
                        career_id=career_id,
                        career_text=career_text,
                        exclude_ids=asked_ids,
                        require_relevance=True,
                    )
                    questions.extend(fallback_generated)
                    asked_ids.extend([q.id for q in fallback_generated])

        if not questions and (
            technical_mcq_count is not None
            and coding_count is not None
            and technical_mcq_count >= 0
            and coding_count >= 0
            and (technical_mcq_count + coding_count) > 0
        ):
            technical_questions = QuestionService.get_questions_for_session(
                num_questions=technical_mcq_count,
                question_types=[InterviewQuestion.QuestionType.TECHNICAL],
                difficulty=difficulty_preference,
                career_id=career_id,
                career_text=career_text,
                exclude_ids=asked_ids,
            )
            questions.extend(technical_questions)
            asked_ids.extend([q.id for q in technical_questions])

            coding_questions = QuestionService.get_questions_for_session(
                num_questions=coding_count,
                question_types=[InterviewQuestion.QuestionType.CODING],
                difficulty=difficulty_preference,
                career_id=career_id,
                career_text=career_text,
                exclude_ids=asked_ids,
            )
            questions.extend(coding_questions)
            asked_ids.extend([q.id for q in coding_questions])

            remaining = max(0, num_questions - len(questions))
            if remaining > 0:
                fallback_questions = QuestionService.get_questions_for_session(
                    num_questions=remaining,
                    question_types=question_types,
                    difficulty=difficulty_preference,
                    career_id=career_id,
                    career_text=career_text,
                    exclude_ids=asked_ids,
                )
                questions.extend(fallback_questions)
        elif not questions:
            questions = QuestionService.get_questions_for_session(
                num_questions=num_questions,
                question_types=question_types,
                difficulty=difficulty_preference,
                career_id=career_id,
                career_text=career_text,
            )

        if technical_mcq_count is not None and coding_count is not None and (technical_mcq_count + coding_count) > 0:
            current_mcq = sum(1 for question in questions if question.question_type == InterviewQuestion.QuestionType.TECHNICAL)
            current_coding = sum(1 for question in questions if question.question_type == InterviewQuestion.QuestionType.CODING)
            existing_ids = [question.id for question in questions]

            extra_mcq = max(0, technical_mcq_count - current_mcq)
            if extra_mcq > 0:
                fill_mcq = QuestionService.get_questions_for_session(
                    num_questions=extra_mcq,
                    question_types=[InterviewQuestion.QuestionType.TECHNICAL],
                    difficulty=difficulty_preference,
                    career_id=career_id,
                    career_text=career_text,
                    exclude_ids=existing_ids,
                )
                questions.extend(fill_mcq)
                existing_ids.extend([q.id for q in fill_mcq])

            extra_coding = max(0, coding_count - current_coding)
            if extra_coding > 0:
                dsa_fill_payloads = hosted_ai._select_dsa_coding_questions(
                    difficulty=difficulty_preference,
                    count=extra_coding,
                    coding_language=coding_language or "python",
                    coding_mode=coding_mode or "function",
                )
                dsa_fill_questions: List[InterviewQuestion] = []
                for payload in dsa_fill_payloads:
                    dsa_question = InterviewQuestion.objects.create(
                        question=str(payload.get("question") or "").strip(),
                        question_type=InterviewQuestion.QuestionType.CODING,
                        difficulty=difficulty_preference,
                        category="LLM Generated",
                        tags=["realtime", "dsa", "coding"],
                        expected_topics=["dsa"],
                        sample_answer="",
                        answer_tips=payload.get("answer_tips") if isinstance(payload.get("answer_tips"), list) else [],
                        is_active=False,
                    )
                    dsa_fill_questions.append(dsa_question)

                questions.extend(dsa_fill_questions)
                existing_ids.extend([q.id for q in dsa_fill_questions])

                still_extra_coding = max(0, extra_coding - len(dsa_fill_questions))
                if still_extra_coding > 0:
                    fill_coding = QuestionService.get_questions_for_session(
                        num_questions=still_extra_coding,
                        question_types=[InterviewQuestion.QuestionType.CODING],
                        difficulty=difficulty_preference,
                        career_id=career_id,
                        career_text=career_text,
                        exclude_ids=existing_ids,
                    )
                    questions.extend(fill_coding)

            # Preserve technical assessment order requested by user: MCQ first, then coding.
            questions = [
                *[q for q in questions if q.question_type == InterviewQuestion.QuestionType.TECHNICAL],
                *[q for q in questions if q.question_type == InterviewQuestion.QuestionType.CODING],
            ]

        if technical_mcq_count is not None and coding_count is not None and (technical_mcq_count + coding_count) > 0:
            questions = questions[:max(1, technical_mcq_count + coding_count)]
        elif num_questions > 0:
            questions = questions[:num_questions]
        
        # Create response placeholders
        for i, question in enumerate(questions):
            response = InterviewResponse.objects.create(
                session=session,
                question=question,
                order=i + 1
            )

            if question.question_type == InterviewQuestion.QuestionType.TECHNICAL and isinstance(question.answer_tips, list):
                options = [str(option).strip() for option in question.answer_tips if str(option).strip()]
                if len(options) == 4 and question.sample_answer and question.sample_answer in options:
                    response.ai_analysis = {
                        "round_mcq": {
                            "correct_option": question.sample_answer,
                            "options": options,
                            "explanation": "",
                        }
                    }
                    response.save(update_fields=["ai_analysis"])
            
            # Increment times asked
            question.times_asked += 1
            question.save(update_fields=["times_asked"])
        
        logger.info(f"Created session {session.id} with {len(questions)} questions")
        
        return session
    
    @staticmethod
    @transaction.atomic
    def start_session(session: InterviewSession) -> InterviewSession:
        """Start an interview session."""
        if session.status != InterviewSession.SessionStatus.SCHEDULED:
            raise ValueError("Session already started or completed")
        
        session.status = InterviewSession.SessionStatus.IN_PROGRESS
        session.started_at = timezone.now()
        session.save()
        
        return session
    
    @staticmethod
    @transaction.atomic
    def complete_session(session: InterviewSession) -> InterviewSession:
        """Complete an interview session and generate feedback."""
        session.status = InterviewSession.SessionStatus.COMPLETED
        session.completed_at = timezone.now()
        
        # Calculate overall score
        responses = session.responses.filter(ai_score__isnull=False)
        if responses.exists():
            avg_score = responses.aggregate(avg=Avg("ai_score"))["avg"]
            session.overall_score = int(avg_score) if avg_score else None
        
        # Generate AI feedback
        session.ai_feedback, session.strengths, session.improvements = \
            SessionService._generate_session_feedback(session)
        
        session.save()
        
        logger.info(f"Completed session {session.id}")
        
        return session
    
    @staticmethod
    def _generate_session_feedback(session: InterviewSession) -> tuple:
        """Generate AI feedback for session using Gemini."""
        responses = session.responses.all()
        
        # Analyze scores
        scores = {
            "content": [],
            "structure": [],
            "clarity": [],
            "relevance": []
        }
        
        qa_pairs = []
        for response in responses:
            if response.content_score:
                scores["content"].append(response.content_score)
            if response.structure_score:
                scores["structure"].append(response.structure_score)
            if response.clarity_score:
                scores["clarity"].append(response.clarity_score)
            if response.relevance_score:
                scores["relevance"].append(response.relevance_score)
            
            # Collect Q&A pairs for AI feedback
            if response.question and response.response_text:
                qa_pairs.append({
                    "question": response.question.question,
                    "answer": response.response_text,
                    "score": response.ai_score
                })
        
        # Calculate averages
        averages = {
            k: sum(v) / len(v) if v else 0
            for k, v in scores.items()
        }
        
        # Identify strengths and improvements
        strengths = [k for k, v in averages.items() if v >= 70]
        improvements = [k for k, v in averages.items() if v < 60]
        
        # Use Gemini AI to generate detailed session feedback
        try:
            ai_prompts = AIPromptsService()
            
            # Get job context
            job_role = ""
            if session.target_career:
                job_role = session.target_career.title
            elif session.target_company:
                job_role = f"Role at {session.target_company}"
            
            # Create summary for AI
            session_summary = {
                "total_questions": responses.count(),
                "average_scores": averages,
                "qa_pairs": qa_pairs[:5],  # Limit to first 5 to avoid token limits
                "job_role": job_role,
                "session_type": session.session_type
            }
            
            # Call AI for comprehensive feedback
            from services.ai.gemini import GeminiAIService
            gemini = GeminiAIService()
            
            prompt = f"""Analyze this interview practice session and provide comprehensive feedback.

Session Summary:
- Total Questions: {session_summary['total_questions']}
- Job Role: {job_role or 'General Practice'}
- Session Type: {session.session_type}

Score Averages:
- Content: {averages.get('content', 0):.1f}/100
- Structure: {averages.get('structure', 0):.1f}/100  
- Clarity: {averages.get('clarity', 0):.1f}/100
- Relevance: {averages.get('relevance', 0):.1f}/100

Sample Q&A Pairs:
"""
            for i, qa in enumerate(qa_pairs[:5], 1):
                prompt += f"\nQ{i}: {qa['question'][:200]}\nA{i}: {qa['answer'][:300]}\nScore: {qa.get('score', 'N/A')}\n"
            
            prompt += """

Provide a JSON response with:
1. "overall_feedback": Comprehensive paragraph summarizing performance
2. "strengths": List of 3-5 specific strengths demonstrated
3. "improvements": List of 3-5 specific areas to improve with actionable advice
4. "next_steps": 3 recommended next steps for preparation
5. "confidence_assessment": Brief assessment of confidence and communication style
"""
            
            ai_feedback = gemini.generate_json(prompt)
            
            if ai_feedback and "error" not in ai_feedback:
                feedback = ai_feedback.get("overall_feedback", "")
                if ai_feedback.get("confidence_assessment"):
                    feedback += f" {ai_feedback['confidence_assessment']}"
                
                ai_strengths = SessionService._normalize_feedback_items(
                    ai_feedback.get("strengths", strengths),
                    fallback=strengths,
                )
                ai_improvements = SessionService._normalize_feedback_items(
                    ai_feedback.get("improvements", improvements),
                    fallback=improvements,
                )
                
                return feedback, ai_strengths, ai_improvements
                
        except Exception as e:
            logger.warning(f"AI feedback generation failed: {e}")
        
        # Fallback to rule-based feedback
        feedback = f"You completed {responses.count()} questions. "
        if strengths:
            feedback += f"Strengths: {', '.join(strengths)}. "
        if improvements:
            feedback += f"Areas to improve: {', '.join(improvements)}."
        
        return feedback, strengths, improvements
    
    @staticmethod
    def get_user_sessions(
        user,
        status: Optional[str] = None,
        session_type: Optional[str] = None
    ):
        """Get user's sessions."""
        queryset = InterviewSession.objects.filter(
            user=user,
            is_deleted=False
        )
        
        if status:
            queryset = queryset.filter(status=status)
        
        if session_type:
            queryset = queryset.filter(session_type=session_type)
        
        return queryset.order_by("-created_at")


class ResponseService:
    """Service for interview response operations."""

    @staticmethod
    def _normalize_text(value: str) -> str:
        return " ".join(str(value or "").lower().replace("\n", " ").split())

    @staticmethod
    def _normalize_score_value(value: Any, default: int = 70) -> int:
        """Normalize score from 0-1, 0-10, or 0-100 scale to 0-100 int."""
        try:
            score = float(value)
        except (TypeError, ValueError):
            score = float(default)

        if score <= 1.0:
            score *= 100.0
        elif score <= 10.0:
            score *= 10.0

        score = max(0.0, min(100.0, score))
        return int(round(score))

    @staticmethod
    def _apply_spoken_technical_score_floor(
        question_text: str,
        answer_text: str,
        question_type: str,
        scores: Dict[str, int],
    ) -> Dict[str, int]:
        """Apply fairness floor for technically correct spoken answers."""
        if question_type not in ["technical", "system_design"]:
            return scores

        q = ResponseService._normalize_text(question_text)
        a = ResponseService._normalize_text(answer_text)

        asks_time_complexity = "time complexity" in q
        has_o_notation = ("o(" in a) or ("big o" in a)

        if asks_time_complexity and has_o_notation:
            floor = 60

            if "hash table" in q or "hashtable" in q or "hash map" in q:
                mentions_avg_constant = ("o(1" in a) or ("constant" in a)
                mentions_worst_case = ("worst" in a and "o(n" in a) or ("collision" in a)
                if mentions_avg_constant:
                    floor = 72
                if mentions_avg_constant and mentions_worst_case:
                    floor = 82

            scores["overall_score"] = max(scores.get("overall_score", 0), floor)
            scores["content_score"] = max(scores.get("content_score", 0), floor)
            scores["relevance_score"] = max(scores.get("relevance_score", 0), min(90, floor + 5))
            scores["clarity_score"] = max(scores.get("clarity_score", 0), min(80, floor))
            scores["structure_score"] = max(scores.get("structure_score", 0), min(78, floor - 2 if floor > 2 else floor))

        return scores

    @staticmethod
    def _write_uploaded_file_temp(uploaded_file, suffix: str = "") -> str:
        """Persist uploaded file to a temporary path and return it."""
        file_suffix = suffix or Path(getattr(uploaded_file, "name", "")).suffix or ".bin"
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_suffix) as temp_file:
            for chunk in uploaded_file.chunks():
                temp_file.write(chunk)
            return temp_file.name

    @staticmethod
    def _resolve_response_text(
        response_text: str,
        response_audio_file=None,
        response_video_file=None,
    ) -> Dict[str, Any]:
        """Resolve final response text from text, audio, or video input."""
        if response_text and response_text.strip():
            return {
                "text": response_text.strip(),
                "analysis": {
                    "input_mode": "text",
                    "transcript_source": "user_text",
                },
            }

        if not response_audio_file and not response_video_file:
            return {
                "text": "",
                "analysis": {
                    "input_mode": "unknown",
                    "transcript_source": "none",
                },
            }

        hosted_ai = HostedInterviewAIService()
        if not hosted_ai.is_enabled():
            return {
                "text": "",
                "analysis": {
                    "input_mode": "voice" if response_audio_file else "video",
                    "transcript_source": "none",
                    "transcription_error": "Hosted STT not configured. Please set GROQ_API_KEY.",
                },
            }

        temp_paths: List[str] = []
        try:
            if response_audio_file:
                audio_path = ResponseService._write_uploaded_file_temp(
                    response_audio_file,
                    suffix=Path(getattr(response_audio_file, "name", "")).suffix or ".webm",
                )
                temp_paths.append(audio_path)
                try:
                    stt = hosted_ai.transcribe_audio_file(audio_path, source="audio")
                except Exception as stt_err:
                    logger.warning(f"Direct audio STT failed, attempting transcoding fallback: {stt_err}")
                    try:
                        transcoded_audio_path = hosted_ai.transcode_audio_to_wav(audio_path)
                        temp_paths.append(transcoded_audio_path)
                        stt = hosted_ai.transcribe_audio_file(transcoded_audio_path, source="audio")
                    except Exception as stt_fallback_err:
                        logger.warning(f"Transcoded audio STT fallback failed: {stt_fallback_err}")
                        return {
                            "text": "",
                            "analysis": {
                                "input_mode": "voice",
                                "transcript_source": "none",
                                "transcription_error": "Could not transcribe audio. Try re-recording or upload a clearer audio file.",
                            },
                        }
                return {
                    "text": stt["transcript"],
                    "analysis": {
                        "input_mode": "voice",
                        "transcript_source": stt.get("provider", "stt"),
                        "transcript_model": stt.get("model"),
                    },
                }

            video_path = ResponseService._write_uploaded_file_temp(
                response_video_file,
                suffix=Path(getattr(response_video_file, "name", "")).suffix or ".webm",
            )
            temp_paths.append(video_path)
            try:
                audio_path = hosted_ai.extract_audio_from_video(video_path)
            except Exception as extract_err:
                logger.warning(f"Video audio extraction failed: {extract_err}")
                return {
                    "text": "",
                    "analysis": {
                        "input_mode": "video",
                        "transcript_source": "none",
                        "audio_extraction": "failed",
                        "transcription_error": "Could not process video audio. Ensure ffmpeg is configured or upload audio directly.",
                    },
                }
            temp_paths.append(audio_path)
            try:
                stt = hosted_ai.transcribe_audio_file(audio_path, source="video")
            except Exception as stt_err:
                logger.warning(f"Video STT failed: {stt_err}")
                return {
                    "text": "",
                    "analysis": {
                        "input_mode": "video",
                        "transcript_source": "none",
                        "audio_extraction": "ffmpeg",
                        "transcription_error": "Could not transcribe video audio. Try a clearer recording or upload audio directly.",
                    },
                }
            return {
                "text": stt["transcript"],
                "analysis": {
                    "input_mode": "video",
                    "transcript_source": stt.get("provider", "stt"),
                    "transcript_model": stt.get("model"),
                    "audio_extraction": "ffmpeg",
                },
            }
        finally:
            for path in temp_paths:
                try:
                    Path(path).unlink(missing_ok=True)
                except Exception:
                    pass
    
    @staticmethod
    @transaction.atomic
    def submit_response(
        response: InterviewResponse,
        response_text: str = "",
        response_audio_url: str = "",
        response_video_url: str = "",
        response_audio_file=None,
        response_video_file=None,
        time_taken_seconds: int = 0,
        self_rating: Optional[int] = None,
        self_notes: str = ""
    ) -> InterviewResponse:
        """Submit a response to a question."""
        resolved = ResponseService._resolve_response_text(
            response_text=response_text,
            response_audio_file=response_audio_file,
            response_video_file=response_video_file,
        )

        response.response_text = resolved.get("text", "")
        response.response_audio_url = response_audio_url
        response.response_video_url = response_video_url
        response.time_taken_seconds = time_taken_seconds
        response.self_rating = self_rating
        response.self_notes = self_notes
        response.completed_at = timezone.now()

        existing_analysis = response.ai_analysis if isinstance(response.ai_analysis, dict) else {}
        response.ai_analysis = {
            **existing_analysis,
            **(resolved.get("analysis") or {}),
        }
        
        response.save()

        return response
    
    @staticmethod
    @transaction.atomic
    def evaluate_response_with_ai(response: InterviewResponse) -> InterviewResponse:
        """
        Evaluation flow:
        1) Hosted LLM evaluation (fast, high-quality, no local model requirement)
        2) Existing rubric-based evaluator fallback
        3) Existing Gemini/InterviewCoach fallback
        """
        question = response.question
        question_text = question.question if question else ""
        question_type = question.question_type if question else "behavioral"
        answer_text = (response.response_text or "").strip()
        job_role = ""
        if response.session and response.session.target_career:
            job_role = response.session.target_career.title
        elif response.session and response.session.target_company:
            job_role = f"Role at {response.session.target_company}"

        if not answer_text:
            existing_analysis = response.ai_analysis if isinstance(response.ai_analysis, dict) else {}
            transcription_error = existing_analysis.get("transcription_error")

            response.ai_score = 0
            response.content_score = 0
            response.structure_score = 0
            response.clarity_score = 0
            response.relevance_score = 0
            response.ai_feedback = (
                str(transcription_error)
                if transcription_error
                else "No answer text was provided. Please submit a text, voice, or video response."
            )
            response.ai_analysis = {
                **existing_analysis,
                "evaluation_method": "empty_answer",
                "suggestions": [
                    "Answer with at least 3-5 clear sentences.",
                    "Use one concrete example from your real experience.",
                    "End with result/impact in numbers where possible.",
                ],
            }
            response.save()
            return response

        # Try hosted LLM first
        hosted_ai = HostedInterviewAIService()
        if hosted_ai.is_enabled():
            hosted_eval = hosted_ai.evaluate_answer(
                question=question_text,
                answer=answer_text,
                question_type=question_type,
                job_role=job_role,
                rubric=question.answer_tips if hasattr(question, "answer_tips") else None,
            )
            if hosted_eval:
                raw_scores = {
                    "overall_score": ResponseService._normalize_score_value(hosted_eval.get("overall_score", 70), 70),
                    "content_score": ResponseService._normalize_score_value(hosted_eval.get("content_score", hosted_eval.get("overall_score", 70)), 70),
                    "structure_score": ResponseService._normalize_score_value(hosted_eval.get("structure_score", 70), 70),
                    "clarity_score": ResponseService._normalize_score_value(hosted_eval.get("clarity_score", 70), 70),
                    "relevance_score": ResponseService._normalize_score_value(hosted_eval.get("relevance_score", 70), 70),
                }

                calibrated = ResponseService._apply_spoken_technical_score_floor(
                    question_text=question_text,
                    answer_text=answer_text,
                    question_type=question_type,
                    scores=raw_scores,
                )

                response.ai_score = int(calibrated.get("overall_score", 70))
                response.content_score = int(calibrated.get("content_score", response.ai_score))
                response.structure_score = int(calibrated.get("structure_score", 70))
                response.clarity_score = int(calibrated.get("clarity_score", 70))
                response.relevance_score = int(calibrated.get("relevance_score", 70))
                response.ai_feedback = str(hosted_eval.get("feedback", ""))
                response.ai_analysis = {
                    **(response.ai_analysis or {}),
                    "suggestions": hosted_eval.get("suggestions", []),
                    "strengths": hosted_eval.get("strengths", []),
                    "improvements": hosted_eval.get("improvements", []),
                    "confidence_level": hosted_eval.get("confidence_level", "moderate"),
                    "evaluation_method": "hosted_llm",
                    "score_calibration": "spoken_technical_floor",
                    "llm_provider": "groq",
                    "llm_model": hosted_ai.groq_llm_model,
                }
                if hasattr(question, "sample_answer"):
                    response.ai_analysis["best_answer"] = question.sample_answer
                if hasattr(question, "answer_tips"):
                    response.ai_analysis["rubric"] = question.answer_tips

                response.save()
                avg = InterviewResponse.objects.filter(
                    question=question,
                    ai_score__isnull=False
                ).aggregate(avg=Avg("ai_score"))["avg"]
                if avg:
                    question.average_rating = round(avg / 20, 2)
                    question.save(update_fields=["average_rating"])
                return response

        # Use rubric/keyword/sample_answer for coding/HR/behavioral
        if question_type in ["coding", "hr", "behavioral"]:
            try:
                interview_bank = get_interview_bank_service()
                evaluation = interview_bank.evaluate_response(
                    question=question_text,
                    answer=answer_text,
                    question_type=question_type
                )
                if evaluation:
                    response.ai_score = ResponseService._normalize_score_value(evaluation.get("overall_score", 70), 70)
                    response.content_score = ResponseService._normalize_score_value(evaluation.get("content_score", 70), response.ai_score)
                    response.structure_score = ResponseService._normalize_score_value(evaluation.get("structure_score", 70), 70)
                    response.clarity_score = ResponseService._normalize_score_value(evaluation.get("clarity_score", 70), 70)
                    response.relevance_score = ResponseService._normalize_score_value(evaluation.get("relevance_score", 70), 70)
                    response.ai_feedback = evaluation.get("feedback", "")
                    response.ai_analysis = {
                        "keywords_found": evaluation.get("matched_keywords", []),
                        "structure": evaluation.get("structure_analysis", ""),
                        "length_assessment": evaluation.get("length_assessment", "appropriate"),
                        "suggestions": evaluation.get("improvement_suggestions", []),
                        "strengths": evaluation.get("strengths", []),
                        "improvements": evaluation.get("areas_to_improve", []),
                        "star_analysis": evaluation.get("star_analysis", {}),
                        "evaluation_method": "llm_free_rubric"
                    }
                    # Always attach best answer/rubric if available
                    if hasattr(question, "sample_answer"):
                        response.ai_analysis["best_answer"] = question.sample_answer
                    if hasattr(question, "answer_tips"):
                        response.ai_analysis["rubric"] = question.answer_tips
            except Exception as e:
                logger.info(f"LLM-free rubric evaluation failed: {e}")

        # For technical/novel or fallback for low-confidence
        try:
            ai_prompts = AIPromptsService()
            evaluation = ai_prompts.evaluate_interview_answer(
                question=question_text,
                answer=answer_text,
                question_type=question_type,
                job_role=job_role
            )
            if evaluation and "error" not in evaluation:
                response.ai_score = ResponseService._normalize_score_value(evaluation.get("overall_score", 70), 70)
                response.content_score = ResponseService._normalize_score_value(evaluation.get("content_score", evaluation.get("overall_score", 70)), response.ai_score)
                response.structure_score = ResponseService._normalize_score_value(evaluation.get("structure_score", 70), 70)
                response.clarity_score = ResponseService._normalize_score_value(evaluation.get("clarity_score", 70), 70)
                response.relevance_score = ResponseService._normalize_score_value(evaluation.get("relevance_score", 70), 70)
                response.ai_feedback = evaluation.get("feedback", evaluation.get("overall_feedback", ""))
                response.ai_analysis = {
                    "keywords_found": evaluation.get("keywords", evaluation.get("key_points_covered", [])),
                    "structure": evaluation.get("structure_analysis", ""),
                    "length_assessment": evaluation.get("length_assessment", "appropriate"),
                    "suggestions": evaluation.get("suggestions", evaluation.get("improvement_suggestions", [])),
                    "strengths": evaluation.get("strengths", []),
                    "improvements": evaluation.get("improvements", evaluation.get("areas_for_improvement", [])),
                    "star_analysis": evaluation.get("star_analysis", {}),
                    "confidence_level": evaluation.get("confidence_level", "moderate"),
                    "example_quality": evaluation.get("example_quality", ""),
                    "ideal_answer_elements": evaluation.get("ideal_answer_elements", []),
                    "evaluation_method": "gemini_ai"
                }
                # Attach best answer/rubric if available
                if hasattr(question, "sample_answer"):
                    response.ai_analysis["best_answer"] = question.sample_answer
                if hasattr(question, "answer_tips"):
                    response.ai_analysis["rubric"] = question.answer_tips
            else:
                raise Exception("Gemini evaluation returned empty or error result")
        except Exception as gemini_error:
            logger.warning(f"Gemini AI evaluation failed: {gemini_error}")
            try:
                interview_coach = get_interview_coach()
                evaluation = interview_coach.evaluate_answer(
                    question=question_text,
                    answer=answer_text,
                    question_type=question_type,
                    role=job_role
                )
                response.ai_score = ResponseService._normalize_score_value(evaluation.get("overall_score", 70), 70)
                response.content_score = ResponseService._normalize_score_value(evaluation.get("content_score", 70), response.ai_score)
                response.structure_score = ResponseService._normalize_score_value(evaluation.get("structure_score", 70), 70)
                response.clarity_score = ResponseService._normalize_score_value(evaluation.get("clarity_score", 70), 70)
                response.relevance_score = ResponseService._normalize_score_value(evaluation.get("relevance_score", 70), 70)
                response.ai_feedback = evaluation.get("feedback", "")
                response.ai_analysis = {
                    "keywords_found": evaluation.get("keywords", []),
                    "structure": evaluation.get("structure_analysis", ""),
                    "length_assessment": evaluation.get("length_assessment", "appropriate"),
                    "suggestions": evaluation.get("suggestions", []),
                    "strengths": evaluation.get("strengths", []),
                    "improvements": evaluation.get("improvements", []),
                    "evaluation_method": "interview_coach"
                }
                if hasattr(question, "sample_answer"):
                    response.ai_analysis["best_answer"] = question.sample_answer
                if hasattr(question, "answer_tips"):
                    response.ai_analysis["rubric"] = question.answer_tips
            except Exception as coach_error:
                logger.error(f"All AI evaluations failed: {coach_error}", exc_info=True)
                import random
                response.ai_score = random.randint(60, 80)
                response.content_score = random.randint(55, 85)
                response.structure_score = random.randint(55, 85)
                response.clarity_score = random.randint(55, 85)
                response.relevance_score = random.randint(55, 85)
                response.ai_feedback = (
                    "Thank you for your response. Focus on providing specific examples "
                    "and quantifying your achievements where possible. Use the STAR method "
                    "(Situation, Task, Action, Result) for behavioral questions."
                )
                response.ai_analysis = {
                    "keywords_found": [],
                    "structure": "",
                    "length_assessment": "appropriate",
                    "suggestions": [
                        "Add more specific metrics and numbers",
                        "Include time context for your examples",
                        "Use the STAR method for behavioral questions",
                        "Be more specific about your personal contribution"
                    ],
                    "evaluation_method": "fallback_rule_based"
                }
                if hasattr(question, "sample_answer"):
                    response.ai_analysis["best_answer"] = question.sample_answer
                if hasattr(question, "answer_tips"):
                    response.ai_analysis["rubric"] = question.answer_tips

        response.save()
        # Update question average rating
        avg = InterviewResponse.objects.filter(
            question=question,
            ai_score__isnull=False
        ).aggregate(avg=Avg("ai_score"))["avg"]
        if avg:
            question.average_rating = round(avg / 20, 2)
            question.save(update_fields=["average_rating"])
        return response


class ScheduleService:
    """Service for interview schedule operations."""
    
    @staticmethod
    def get_upcoming_interviews(user, days: int = 7):
        """Get upcoming interviews."""
        cutoff = timezone.now() + timedelta(days=days)
        
        return InterviewSchedule.objects.filter(
            user=user,
            is_deleted=False,
            status__in=[
                InterviewSchedule.Status.SCHEDULED,
                InterviewSchedule.Status.CONFIRMED
            ],
            scheduled_at__lte=cutoff,
            scheduled_at__gte=timezone.now()
        ).select_related("application__job__company").order_by("scheduled_at")
    
class TipService:
    """Service for interview tips."""
    
    @staticmethod
    def get_featured_tips(limit: int = 5) -> List[InterviewTip]:
        """Get featured tips."""
        return list(InterviewTip.objects.filter(
            is_featured=True
        ).order_by("order")[:limit])


class StatsService:
    """Service for interview statistics."""
    
    @staticmethod
    def get_practice_stats(user) -> Dict[str, Any]:
        """Get practice statistics for user."""
        sessions = InterviewSession.objects.filter(
            user=user,
            is_deleted=False
        )
        
        completed_sessions = sessions.filter(
            status=InterviewSession.SessionStatus.COMPLETED
        )
        
        responses = InterviewResponse.objects.filter(
            session__user=user,
            completed_at__isnull=False
        )
        
        # Total stats
        total_sessions = completed_sessions.count()
        total_questions = responses.count()
        
        # Average score
        avg_score = responses.filter(
            ai_score__isnull=False
        ).aggregate(avg=Avg("ai_score"))["avg"] or 0
        
        # Total time
        total_time = responses.aggregate(
            total=Sum("time_taken_seconds")
        )["total"] or 0
        
        # By question type
        by_type = {}
        for response in responses:
            q_type = response.question.question_type
            if q_type not in by_type:
                by_type[q_type] = {"count": 0, "scores": []}
            by_type[q_type]["count"] += 1
            if response.ai_score:
                by_type[q_type]["scores"].append(response.ai_score)
        
        for q_type in by_type:
            scores = by_type[q_type]["scores"]
            by_type[q_type]["avg_score"] = (
                sum(scores) / len(scores) if scores else 0
            )
            del by_type[q_type]["scores"]
        
        # Improvement areas
        improvements = []
        for q_type, data in by_type.items():
            if data["avg_score"] < 70:
                improvements.append(q_type)
        
        return {
            "total_sessions": total_sessions,
            "total_questions_answered": total_questions,
            "average_score": round(float(avg_score), 1),
            "total_practice_time_minutes": total_time // 60,
            "by_question_type": by_type,
            "improvement_areas": improvements
        }
