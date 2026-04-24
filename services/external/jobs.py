"""Job search integration service backed by RapidAPI JSearch."""

from __future__ import annotations

import logging
import time
from typing import Any

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class JSearchJobSearchService:
    """Wrapper around JSearch API that normalizes payloads for frontend use."""

    _CACHE_VERSION = 2
    _CACHE: dict[tuple[Any, ...], tuple[float, dict[str, Any]]] = {}
    _SESSION: requests.Session | None = None

    def __init__(self) -> None:
        self.api_key = getattr(settings, "JSEARCH_API_KEY", "")
        self.base_url = getattr(settings, "JSEARCH_API_URL", "https://jsearch.p.rapidapi.com").rstrip("/")
        self.timeout_seconds = float(getattr(settings, "JSEARCH_TIMEOUT_SECONDS", 7.0))
        self.cache_ttl_seconds = int(getattr(settings, "JSEARCH_CACHE_TTL_SECONDS", 300))
        if self.__class__._SESSION is None:
            session = requests.Session()
            session.headers.update({"Accept": "application/json"})
            self.__class__._SESSION = session

    def _headers(self) -> dict[str, str]:
        return {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
        }

    @property
    def _session(self) -> requests.Session:
        session = self.__class__._SESSION
        if session is None:
            session = requests.Session()
            session.headers.update({"Accept": "application/json"})
            self.__class__._SESSION = session
        return session

    def _build_query(
        self,
        query: str,
        location: str | None,
        job_type: str | None = None,
        work_mode: str | None = None,
        experience_level: str | None = None,
    ) -> str:
        q = (query or "Software Developer").strip()
        parts = [q]

        job_type_value = (job_type or "").strip().lower()
        if job_type_value == "internship" and "intern" not in q.lower():
            parts.append("internship")
        elif job_type_value == "contract" and "contract" not in q.lower():
            parts.append("contract")

        work_mode_value = (work_mode or "").strip().lower()
        if work_mode_value == "remote" and "remote" not in q.lower():
            parts.append("remote")

        location_value = (location or "").strip().lower()
        if location_value and location_value not in {"india", "remote", "any", "global", "worldwide"}:
            parts.append(location.strip())

        return " ".join(dict.fromkeys(parts))

    def _normalize_job(self, raw: dict[str, Any]) -> dict[str, Any]:
        highlights = raw.get("job_highlights") or {}
        qualifications = highlights.get("Qualifications") or []

        city = (raw.get("job_city") or "").strip()
        state = (raw.get("job_state") or "").strip()
        country = (raw.get("job_country") or "").strip()
        location_parts = [p for p in [city, state, country] if p]

        salary_min = raw.get("job_min_salary")
        salary_max = raw.get("job_max_salary")

        title = (raw.get("job_title") or "").strip()
        description = raw.get("job_description") or ""
        location_text = (raw.get("job_location") or "").lower()
        lower_text = f"{title} {description} {location_text}".lower()

        is_remote = bool(raw.get("job_is_remote"))
        if is_remote:
            work_mode = "remote"
        elif "hybrid" in lower_text:
            work_mode = "hybrid"
        else:
            work_mode = "onsite"

        exp_required = raw.get("job_required_experience") or {}
        months = None
        if isinstance(exp_required, dict):
            months = exp_required.get("required_experience_in_months")
        if not isinstance(months, (int, float)):
            months = None

        experience_level = self._infer_experience_level(months, lower_text)

        return {
            "id": str(raw.get("job_id") or raw.get("job_google_link") or ""),
            "title": title or "Untitled Role",
            "company": raw.get("employer_name") or "Unknown Company",
            "company_logo": raw.get("employer_logo") or "",
            "location": ", ".join(location_parts) if location_parts else (raw.get("job_location") or "Remote"),
            "job_type": self._normalize_job_type(raw.get("job_employment_type")),
            "work_mode": work_mode,
            "salary_min": salary_min if isinstance(salary_min, (int, float)) else None,
            "salary_max": salary_max if isinstance(salary_max, (int, float)) else None,
            "salary_currency": raw.get("job_salary_currency") or "USD",
            "description": description,
            "requirements": qualifications if isinstance(qualifications, list) else [],
            "skills_required": qualifications if isinstance(qualifications, list) else [],
            "experience_level": experience_level,
            "experience_required_months": months,
            "posted_date": raw.get("job_posted_at_datetime_utc") or raw.get("job_posted_at") or "",
            "apply_url": raw.get("job_apply_link") or "",
            "source_url": raw.get("job_google_link") or "",
            "source": raw.get("job_publisher") or "JSearch",
        }

    def _normalize_job_type(self, raw_job_type: Any) -> str:
        value = str(raw_job_type or "").lower().replace("_", "-")
        if "intern" in value:
            return "internship"
        if "part" in value:
            return "part-time"
        if "contract" in value:
            return "contract"
        if "full" in value:
            return "full-time"
        return value or "full-time"

    def _map_job_type_for_api(self, job_type: str) -> str:
        mapping = {
            "full-time": "FULLTIME",
            "part-time": "PARTTIME",
            "internship": "INTERN",
            "contract": "CONTRACTOR",
        }
        return mapping.get(job_type.lower().strip(), job_type)

    def _country_code_for_location(self, location: str | None) -> str | None:
        value = (location or "").strip().lower()
        if not value:
            return None
        mapping = {
            "india": "in",
            "united states": "us",
            "usa": "us",
            "us": "us",
            "united kingdom": "gb",
            "uk": "gb",
            "canada": "ca",
            "australia": "au",
            "singapore": "sg",
            "germany": "de",
            "france": "fr",
            "remote": None,
            "any": None,
            "global": None,
            "worldwide": None,
        }
        if value in mapping:
            return mapping[value]
        return None

    def _build_job_record(
        self,
        *,
        job_id: str,
        title: str,
        company: str,
        location: str,
        job_type: str,
        work_mode: str,
        salary_min: int | float | None = None,
        salary_max: int | float | None = None,
        salary_currency: str = "USD",
        description: str = "",
        requirements: list[str] | None = None,
        experience_level: str = "mid",
        experience_required_months: int | float | None = None,
        posted_date: str = "",
        apply_url: str = "",
        source_url: str = "",
        source: str = "JSearch",
        company_logo: str = "",
    ) -> dict[str, Any]:
        return {
            "id": str(job_id or ""),
            "title": title or "Untitled Role",
            "company": company or "Unknown Company",
            "company_logo": company_logo or "",
            "location": location or "Remote",
            "job_type": job_type or "full-time",
            "work_mode": work_mode or "remote",
            "salary_min": salary_min if isinstance(salary_min, (int, float)) else None,
            "salary_max": salary_max if isinstance(salary_max, (int, float)) else None,
            "salary_currency": salary_currency or "USD",
            "description": description or "",
            "requirements": requirements or [],
            "skills_required": requirements or [],
            "experience_level": experience_level or "mid",
            "experience_required_months": experience_required_months,
            "posted_date": posted_date or "",
            "apply_url": apply_url or "",
            "source_url": source_url or "",
            "source": source or "JSearch",
        }

    def _infer_experience_level(self, months: int | float | None, lower_text: str) -> str:
        lead_keywords = ["lead", "manager", "principal", "architect", "staff"]
        entry_keywords = ["intern", "fresher", "entry", "junior", "graduate"]

        if any(k in lower_text for k in lead_keywords):
            return "lead"
        if any(k in lower_text for k in entry_keywords):
            return "entry"
        if months is None:
            return "mid"
        if months >= 96:
            return "lead"
        if months >= 60:
            return "senior"
        if months >= 24:
            return "mid"
        return "entry"

    def _matches_experience_level(self, job: dict[str, Any], level: str) -> bool:
        expected = (level or "").lower().strip()
        actual = str(job.get("experience_level") or "").lower().strip()
        return not expected or expected == actual

    def _relevance_score(self, job: dict[str, Any], query: str, location: str | None) -> int:
        score = 0
        query_text = (query or "").strip().lower()
        title = str(job.get("title") or "").lower()
        company = str(job.get("company") or "").lower()
        description = str(job.get("description") or "").lower()
        skills = " ".join(str(s).lower() for s in (job.get("skills_required") or []))
        haystack = f"{title} {company} {description} {skills}"

        if query_text:
            query_tokens = [token for token in query_text.replace("/", " ").replace("-", " ").split() if len(token) > 1]
            for token in query_tokens:
                if token in title:
                    score += 6
                elif token in haystack:
                    score += 3
            if query_text in title:
                score += 8
            elif query_text in haystack:
                score += 4

        if location:
            location_text = location.strip().lower()
            if location_text in str(job.get("location") or "").lower():
                score += 3

        work_mode = str(job.get("work_mode") or "").lower()
        if work_mode == "remote":
            score += 1

        experience_level = str(job.get("experience_level") or "").lower()
        if experience_level in {"entry", "mid"}:
            score += 1

        return score

    def _prioritize_jobs(self, jobs: list[dict[str, Any]], query: str, location: str | None) -> list[dict[str, Any]]:
        scored = [
            (self._relevance_score(job, query, location), index, job)
            for index, job in enumerate(jobs)
        ]
        scored.sort(key=lambda item: (-item[0], item[1]))
        return [job for _, _, job in scored]

    def _query_candidates(
        self,
        query: str,
        location: str | None,
        job_type: str | None,
        work_mode: str | None,
        experience_level: str | None,
    ) -> list[str]:
        candidates: list[str] = []
        primary_query = self._build_query(
            query,
            location,
            job_type=job_type,
            work_mode=work_mode,
            experience_level=experience_level,
        )
        if primary_query:
            candidates.append(primary_query)

        broad_query = (query or "").strip() or "Software Developer"
        broad_query = broad_query.replace("Junior", "").replace("Senior", "").replace("Lead", "").replace("Principal", "").strip()
        if broad_query and broad_query not in candidates:
            candidates.append(broad_query)

        for fallback_query in ("Developer", "Software Engineer"):
            if fallback_query not in candidates:
                candidates.append(fallback_query)

        return candidates

    def _cache_key(
        self,
        query: str,
        location: str | None,
        job_type: str | None,
        work_mode: str | None,
        experience_level: str | None,
        remote_jobs_only: bool,
        date_posted: str,
        page: int,
        num_pages: int,
    ) -> tuple[Any, ...]:
        return (
            self._CACHE_VERSION,
            (query or "").strip().lower(),
            (location or "").strip().lower(),
            (job_type or "").strip().lower(),
            (work_mode or "").strip().lower(),
            (experience_level or "").strip().lower(),
            bool(remote_jobs_only),
            (date_posted or "month").strip().lower(),
            int(page),
            int(num_pages),
        )

    def _set_cache(self, key: tuple[Any, ...], result: dict[str, Any]) -> None:
        self._CACHE[key] = (time.time(), result)

    def _get_cache(self, key: tuple[Any, ...], allow_stale: bool = False) -> dict[str, Any] | None:
        cached = self._CACHE.get(key)
        if not cached:
            return None
        ts, result = cached
        age = time.time() - ts
        if age <= self.cache_ttl_seconds or allow_stale:
            source = result.get("source") or "JSearch API"
            return {
                "jobs": result.get("jobs", []),
                "total": result.get("total", 0),
                "source": f"{source} (cached)",
            }
        return None

    def _fallback_jobs(
        self,
        query: str,
        location: str | None,
        remote_jobs_only: bool,
        job_type: str | None = None,
        work_mode: str | None = None,
        experience_level: str | None = None,
    ) -> list[dict[str, Any]]:
        label = location or "India"
        base_title = query or "Software Developer"
        samples: list[dict[str, Any]] = [
            {
                "id": f"fallback-{base_title.lower().replace(' ', '-')}-1",
                "title": f"{base_title} Intern",
                "company": "CareerAI Demo Jobs",
                "company_logo": "",
                "location": label,
                "job_type": "internship",
                "work_mode": "remote",
                "salary_min": None,
                "salary_max": None,
                "salary_currency": "INR",
                "description": "Set JSEARCH_API_KEY in environment to fetch live jobs.",
                "requirements": [],
                "skills_required": [],
                "experience_level": "entry",
                "posted_date": "",
                "apply_url": "",
                "source_url": "",
                "source": "Fallback",
            },
            {
                "id": f"fallback-{base_title.lower().replace(' ', '-')}-2",
                "title": f"Junior {base_title}",
                "company": "CareerAI Demo Jobs",
                "company_logo": "",
                "location": label,
                "job_type": "full-time",
                "work_mode": "onsite",
                "salary_min": None,
                "salary_max": None,
                "salary_currency": "INR",
                "description": "Set JSEARCH_API_KEY in environment to fetch live jobs.",
                "requirements": [],
                "skills_required": [],
                "experience_level": "entry",
                "posted_date": "",
                "apply_url": "",
                "source_url": "",
                "source": "Fallback",
            },
            {
                "id": f"fallback-{base_title.lower().replace(' ', '-')}-3",
                "title": base_title,
                "company": "CareerAI Demo Jobs",
                "company_logo": "",
                "location": label,
                "job_type": "full-time",
                "work_mode": "hybrid",
                "salary_min": None,
                "salary_max": None,
                "salary_currency": "INR",
                "description": "Set JSEARCH_API_KEY in environment to fetch live jobs.",
                "requirements": [],
                "skills_required": [],
                "experience_level": "mid",
                "posted_date": "",
                "apply_url": "",
                "source_url": "",
                "source": "Fallback",
            },
            {
                "id": f"fallback-{base_title.lower().replace(' ', '-')}-4",
                "title": f"Senior {base_title}",
                "company": "CareerAI Demo Jobs",
                "company_logo": "",
                "location": label,
                "job_type": "contract",
                "work_mode": "remote",
                "salary_min": None,
                "salary_max": None,
                "salary_currency": "INR",
                "description": "Set JSEARCH_API_KEY in environment to fetch live jobs.",
                "requirements": [],
                "skills_required": [],
                "experience_level": "senior",
                "posted_date": "",
                "apply_url": "",
                "source_url": "",
                "source": "Fallback",
            },
        ]

        filtered = samples
        if remote_jobs_only:
            filtered = [j for j in filtered if j["work_mode"] == "remote"]
        if work_mode and work_mode.lower() in {"remote", "hybrid", "onsite"}:
            filtered = [j for j in filtered if j["work_mode"] == work_mode.lower()]
        if job_type:
            filtered = [j for j in filtered if j["job_type"] == job_type.lower()]
        if experience_level:
            filtered = [j for j in filtered if j["experience_level"] == experience_level.lower()]

        return filtered or samples

    def search_jobs(
        self,
        query: str,
        location: str | None = None,
        job_type: str | None = None,
        work_mode: str | None = None,
        experience_level: str | None = None,
        remote_jobs_only: bool = False,
        date_posted: str = "week",
        page: int = 1,
        num_pages: int = 1,
    ) -> dict[str, Any]:
        cache_key = self._cache_key(
            query,
            location,
            job_type,
            work_mode,
            experience_level,
            remote_jobs_only,
            date_posted,
            page,
            num_pages,
        )

        cached = self._get_cache(cache_key)
        if cached:
            return cached

        if not self.api_key:
            logger.warning("No JSearch key; falling back to cached or demo jobs")
            stale_cache = self._get_cache(cache_key, allow_stale=True)
            if stale_cache and not str(stale_cache.get("source") or "").startswith("Fallback"):
                return stale_cache
            jobs = self._fallback_jobs(
                query,
                location,
                remote_jobs_only,
                job_type=job_type,
                work_mode=work_mode,
                experience_level=experience_level,
            )
            return {"jobs": jobs, "total": len(jobs), "source": "Fallback"}

        jobs: list[dict[str, Any]] = []
        seen: set[str] = set()

        max_pages = min(max(num_pages, 1), 1)
        start_page = max(page, 1)
        country_code = self._country_code_for_location(location)
        query_candidates = self._query_candidates(query, location, job_type, work_mode, experience_level)

        for request_query in query_candidates:
            candidate_jobs: list[dict[str, Any]] = []
            candidate_seen: set[str] = set()

            for p in range(start_page, start_page + max_pages):
                params: dict[str, Any] = {
                    "query": request_query,
                    "page": p,
                    "num_pages": 1,
                    "date_posted": date_posted or "week",
                }
                if country_code:
                    params["country"] = country_code
                if job_type:
                    params["employment_types"] = self._map_job_type_for_api(job_type)
                if remote_jobs_only:
                    params["remote_jobs_only"] = "true"

                try:
                    response = self._session.get(
                        f"{self.base_url}/search",
                        headers=self._headers(),
                        params=params,
                        timeout=self.timeout_seconds,
                    )
                    response.raise_for_status()
                    payload = response.json() if response.content else {}
                    rows = payload.get("data") or []
                except requests.RequestException as exc:
                    logger.warning("JSearch request failed for query '%s' on page %s: %s", request_query, p, exc)
                    rows = []

                for row in rows:
                    normalized = self._normalize_job(row)
                    job_id = normalized.get("id") or ""
                    if job_id and job_id in candidate_seen:
                        continue
                    if job_id:
                        candidate_seen.add(job_id)
                    candidate_jobs.append(normalized)

                if len(candidate_jobs) >= 25:
                    break

            if candidate_jobs:
                jobs = candidate_jobs
                seen = candidate_seen
                break

        if work_mode and work_mode.lower() in {"remote", "hybrid", "onsite"}:
            jobs = [j for j in jobs if j.get("work_mode") == work_mode.lower()]

        if experience_level:
            preferred = [j for j in jobs if self._matches_experience_level(j, experience_level)]
            if preferred:
                jobs = preferred + [j for j in jobs if j not in preferred]

        jobs = self._prioritize_jobs(jobs, query, location)

        if query:
            query_tokens = [token for token in query.lower().replace("/", " ").replace("-", " ").split() if len(token) > 1]
            strong_matches = [job for job in jobs if any(token in str(job.get("title") or "").lower() for token in query_tokens)]
            if strong_matches:
                jobs = strong_matches + [job for job in jobs if job not in strong_matches]

        if jobs:
            live_result = {"jobs": jobs, "total": len(jobs), "source": "JSearch API"}
            self._set_cache(cache_key, live_result)
            return live_result

        stale_cache = self._get_cache(cache_key, allow_stale=True)
        if stale_cache and not str(stale_cache.get("source") or "").startswith("Fallback"):
            return stale_cache

        if not jobs:
            fallback = self._fallback_jobs(
                query,
                location,
                remote_jobs_only,
                job_type=job_type,
                work_mode=work_mode,
                experience_level=experience_level,
            )
            return {"jobs": fallback, "total": len(fallback), "source": "Fallback"}


def get_job_search_service() -> JSearchJobSearchService:
    return JSearchJobSearchService()
