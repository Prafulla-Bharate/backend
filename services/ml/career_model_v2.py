"""
services/ml/career_model_v2.py
------------------------------
Inference-only career prediction module.

Loads the trained model bundle from:
    data/models/career_model_latest.pkl

The model is trained by:
    python training/train_career_model.py

This module is imported by apps/career/services.py:
    from services.ml.career_model_v2 import get_career_prediction_model

Profile dict keys expected by predict():
    skills            : list[str]   — plain skill names
    experience_years  : float       — total years
    current_job_title : str         — most recent job title
    education_degree  : str         — bachelor/master/phd/diploma/btech/mtech/mca
    field_of_study    : str         — Computer Science / ECE / etc.
    certifications    : list[str]   — certification names (may be empty)
    industry          : str         — company industry
"""

from __future__ import annotations

import logging
import pickle
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────────────────────────────────────
_MODULE_DIR = Path(__file__).resolve().parent          # services/ml/
_PROJECT_ROOT = _MODULE_DIR.parent.parent              # CareerAI/
_LATEST_MODEL_PATH = _PROJECT_ROOT / "data" / "models" / "career_model_latest.pkl"

# ─────────────────────────────────────────────────────────────────────────────
# Degree + field normalisation (mirrors train_career_model.py — keep in sync)
# ─────────────────────────────────────────────────────────────────────────────
_DEGREE_MAP = {
    "diploma": 0,
    "bachelor": 1,
    "btech": 1,
    "mca": 2,
    "master": 2,
    "mtech": 2,
    "mba": 2,
    "phd": 3,
}

_FIELD_GROUPS = {
    "cs": ["computer science", "software engineering", "software", "computer"],
    "it": ["information technology", "it", "information system"],
    "ece": ["electronics", "ece", "electrical", "communication", "embedded"],
    "other_tech": [
        "mechanical", "civil", "chemical", "aerospace",
        "automation", "robotics", "instrumentation", "manufacturing",
    ],
    "nontech_mgmt": [
        "business", "mba", "management", "commerce", "economics",
        "marketing", "finance", "hr", "administration", "bba", "bcom",
    ],
    "other": [],
}
_FIELD_GROUP_KEYS = ["cs", "it", "ece", "other_tech", "nontech_mgmt", "other"]


def _normalise_field(raw: str) -> str:
    txt = raw.lower().strip()
    for group, keywords in _FIELD_GROUPS.items():
        if any(kw in txt for kw in keywords):
            return group
    return "other"


def _experience_bucket(years: float) -> int:
    if years < 0.5:
        return 0
    elif years < 2.0:
        return 1
    elif years < 6.0:
        return 2
    return 3


def _build_text_feature(profile: dict) -> str:
    # Must exactly mirror train_career_model.py  build_text_feature()
    # Skills + job title + field of study + certification names (NOT just count)
    # Certification names are strong disambiguation signals:
    #   "oscp" / "ceh" → Cybersecurity,  "pmp" → PM/BA,
    #   "salesforce platform developer" → Salesforce Dev, etc.
    skills = " ".join(str(s).strip().lower() for s in profile.get("skills", []))
    title  = str(profile.get("current_job_title", "")).strip().lower()
    field  = str(profile.get("field_of_study",    "")).strip().lower()
    certs  = " ".join(str(c).strip().lower() for c in profile.get("certifications", []))
    return f"{skills} {title} {field} {certs}".strip()


def _build_industry_text(profile: dict) -> str:
    return str(profile.get("industry", "")).strip().lower()


# ─────────────────────────────────────────────────────────────────────────────
# Result dataclass
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class CareerPredictionResult:
    """Returned by CareerPredictor.predict()."""

    predicted_career: str = ""
    confidence: float = 0.0
    top_predictions: list = field(default_factory=list)
    # top_predictions entries: [{"career": str, "score": float}, ...]

    model_version: int = 0
    n_training_profiles: int = 0


# ─────────────────────────────────────────────────────────────────────────────
# Predictor
# ─────────────────────────────────────────────────────────────────────────────

class CareerPredictor:
    """
    Thin inference wrapper around the trained LightGBM+RF voting ensemble.

    Usage:
        predictor = CareerPredictor.load()
        result = predictor.predict({
            "skills": ["Python", "Django"],
            "experience_years": 2.0,
            "current_job_title": "Software Developer",
            "education_degree": "btech",
            "field_of_study": "Computer Science",
            "certifications": [],
            "industry": "IT Services",
        })
        print(result.predicted_career, result.confidence)
    """

    def __init__(self, bundle: dict):
        self._model = bundle["model"]
        self._le = bundle["label_encoder"]
        self._tfidf_skill = bundle["tfidf_skill"]
        self._tfidf_ind = bundle["tfidf_ind"]
        self._version = bundle.get("version", 0)
        self._n_profiles = bundle.get("n_profiles", 0)
        self._trained = True
        logger.info(
            "CareerPredictor loaded: version=%d  n_profiles=%d",
            self._version,
            self._n_profiles,
        )

    # ── Singleton factory ─────────────────────────────────────────────────
    @classmethod
    def load(cls, model_path: Optional[Path] = None) -> "CareerPredictor":
        path = Path(model_path) if model_path else _LATEST_MODEL_PATH
        if not path.exists():
            raise FileNotFoundError(
                f"No trained model found at {path}.\n"
                "Train the model first:  python training/train_career_model.py"
            )
        with open(path, "rb") as f:
            bundle = pickle.load(f)
        return cls(bundle)

    # ── Properties ────────────────────────────────────────────────────────
    @property
    def is_trained(self) -> bool:
        return self._trained

    @property
    def version(self) -> int:
        return self._version

    # ── Feature encoding ─────────────────────────────────────────────────
    def _encode(self, profile: dict):
        """Build a (1, D) sparse feature matrix for a single profile."""
        import numpy as np
        from scipy.sparse import csr_matrix, hstack

        text = _build_text_feature(profile)
        industry = _build_industry_text(profile)
        bucket = _experience_bucket(float(profile.get("experience_years", 0)))
        degree_raw = str(profile.get("education_degree", "bachelor")).lower().strip()
        degree_ord = _DEGREE_MAP.get(degree_raw, 1)
        field_grp = _normalise_field(str(profile.get("field_of_study", "")))
        field_idx = _FIELD_GROUP_KEYS.index(field_grp)
        cert_count = len(profile.get("certifications", []))

        # TF-IDF transforms — unknown tokens get 0 weight, no crash
        X_text = self._tfidf_skill.transform([text])
        X_ind = self._tfidf_ind.transform([industry])

        # One-hot dense features
        bucket_ohe = np.zeros((1, 4), dtype=np.float32)
        bucket_ohe[0, bucket] = 1.0

        degree_ohe = np.zeros((1, 4), dtype=np.float32)
        degree_ohe[0, min(degree_ord, 3)] = 1.0

        field_ohe = np.zeros((1, 6), dtype=np.float32)
        field_ohe[0, field_idx] = 1.0

        cert_col = np.array([[cert_count]], dtype=np.float32)

        dense = np.hstack([bucket_ohe, degree_ohe, field_ohe, cert_col])
        X_dense = csr_matrix(dense)

        return hstack([X_text, X_ind, X_dense]).tocsr()

    # ── Prediction ────────────────────────────────────────────────────────
    def predict(self, profile: dict, top_n: int = 5) -> CareerPredictionResult:
        """
        Predict career(s) for a user profile.

        Args:
            profile : dict with profile keys (skills, experience_years, etc.)
            top_n   : number of top predictions to return (default 5)

        Returns:
            CareerPredictionResult with predicted_career, confidence, top_predictions
        """
        try:
            import numpy as np

            X = self._encode(profile)
            proba = self._model.predict_proba(X)[0]          # shape (n_classes,)
            top_indices = np.argsort(proba)[::-1][:top_n]

            top_predictions = [
                {
                    "career": str(self._le.classes_[i]),
                    "score": round(float(proba[i]), 4),
                }
                for i in top_indices
            ]

            best = top_predictions[0]
            return CareerPredictionResult(
                predicted_career=best["career"],
                confidence=best["score"],
                top_predictions=top_predictions,
                model_version=self._version,
                n_training_profiles=self._n_profiles,
            )

        except Exception as exc:
            logger.error(
                "CareerPredictor.predict failed: %s", exc, exc_info=True
            )
            return CareerPredictionResult(
                predicted_career="",
                confidence=0.0,
                top_predictions=[],
            )


# ─────────────────────────────────────────────────────────────────────────────
# Backward-compatible alias  (old code used DynamicCareerPredictor)
# ─────────────────────────────────────────────────────────────────────────────
DynamicCareerPredictor = CareerPredictor


# ─────────────────────────────────────────────────────────────────────────────
# Singleton accessor  (imported by apps/career/services.py)
# ─────────────────────────────────────────────────────────────────────────────
_singleton: Optional[CareerPredictor] = None


def get_career_prediction_model() -> CareerPredictor:
    """
    Return the loaded CareerPredictor singleton.
    Loads on first call; subsequent calls return the cached instance.
    Raises FileNotFoundError if no model has been trained yet.
    """
    global _singleton
    if _singleton is None:
        _singleton = CareerPredictor.load()
    return _singleton


def reload_model() -> CareerPredictor:
    """Force-reload the model from disk (call after retraining without restart)."""
    global _singleton
    _singleton = CareerPredictor.load()
    return _singleton
