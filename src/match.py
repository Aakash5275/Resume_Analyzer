"""Resume–JD matching: hybrid lexical + structured skill/experience score."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

import numpy as np

from .extract import ExtractedProfile, extract_profile, text_has_skill
from .tfidf import tfidf_cosine

DEFAULT_WEIGHTS = {
    "skill_coverage": 0.65,
    "tfidf_similarity": 0.18,
    "experience_fit": 0.0,
    "education_fit": 0.12,
    "preferred_bonus": 0.05,
}


@dataclass
class MatchBreakdown:
    skill_coverage: float
    tfidf_similarity: float
    experience_fit: float
    education_fit: float
    preferred_bonus: float

    def as_percent(self) -> Dict[str, float]:
        return {
            "Skill coverage": round(self.skill_coverage * 100, 1),
            "TF-IDF similarity": round(self.tfidf_similarity * 100, 1),
            "Experience fit": round(self.experience_fit * 100, 1),
            "Education fit": round(self.education_fit * 100, 1),
            "Preferred skills": round(self.preferred_bonus * 100, 1),
        }


@dataclass
class MatchResult:
    overall_score: float
    breakdown: MatchBreakdown
    resume_profile: ExtractedProfile
    jd_profile: ExtractedProfile
    matched_required: List[str] = field(default_factory=list)
    missing_required: List[str] = field(default_factory=list)
    matched_preferred: List[str] = field(default_factory=list)
    missing_preferred: List[str] = field(default_factory=list)
    extra_skills: List[str] = field(default_factory=list)
    weights: Dict[str, float] = field(default_factory=lambda: dict(DEFAULT_WEIGHTS))


def skill_coverage(resume_skills: Sequence[str], required: Sequence[str]) -> float:
    if not required:
        return 1.0 if resume_skills else 0.0
    resume_set = set(resume_skills)
    hit = sum(1 for s in required if s in resume_set)
    return hit / len(required)


def experience_fit(resume_years: Optional[float], required_years: Optional[float]) -> float:
    if required_years is None or required_years <= 0:
        if resume_years is None:
            return 0.5
        return float(np.clip(0.55 + min(resume_years, 10) / 25.0, 0.0, 1.0))
    if resume_years is None:
        return 0.35
    ratio = resume_years / required_years
    if ratio >= 1.0:
        return 1.0
    if ratio >= 0.7:
        return 0.75 + 0.25 * ((ratio - 0.7) / 0.3)
    return float(np.clip(ratio * 0.9, 0.0, 0.75))


def education_fit(resume_level: int, jd_level: int) -> float:
    if jd_level <= 0:
        return 0.55 if resume_level >= 2 else 0.5 if resume_level > 0 else 0.45
    if resume_level >= jd_level:
        return 1.0
    if resume_level == 0:
        return 0.3
    gap = jd_level - resume_level
    return 0.7 if gap == 1 else 0.4


def preferred_bonus(resume_skills: Sequence[str], preferred: Sequence[str]) -> float:
    if not preferred:
        return 0.5
    resume_set = set(resume_skills)
    hit = sum(1 for s in preferred if s in resume_set)
    return hit / len(preferred)


def weighted_score(breakdown: MatchBreakdown, weights: Dict[str, float]) -> float:
    total_w = sum(weights.values()) or 1.0
    raw = (
        weights["skill_coverage"] * breakdown.skill_coverage
        + weights["tfidf_similarity"] * breakdown.tfidf_similarity
        + weights["experience_fit"] * breakdown.experience_fit
        + weights["education_fit"] * breakdown.education_fit
        + weights["preferred_bonus"] * breakdown.preferred_bonus
    )
    return float(np.clip(100.0 * raw / total_w, 0.0, 100.0))


def match_resume_to_jd(
    resume_text: str,
    jd_text: str,
    weights: Optional[Dict[str, float]] = None,
    resume_profile: Optional[ExtractedProfile] = None,
    jd_profile: Optional[ExtractedProfile] = None,
) -> MatchResult:
    weights = dict(DEFAULT_WEIGHTS if weights is None else weights)
    resume_profile = resume_profile or extract_profile(resume_text, is_job_description=False)
    jd_profile = jd_profile or extract_profile(jd_text, is_job_description=True)

    required = jd_profile.required_skills or jd_profile.skills
    preferred = jd_profile.preferred_skills
    resume_set = set(resume_profile.skills)
    req_set = set(required)
    pref_set = set(preferred)

    def _on_resume(skill: str) -> bool:
        return skill in resume_set or text_has_skill(resume_text, skill)

    matched_required = sorted(s for s in req_set if _on_resume(s))
    missing_required = sorted(s for s in req_set if not _on_resume(s))
    matched_preferred = sorted(s for s in pref_set if _on_resume(s))
    missing_preferred = sorted(s for s in pref_set if not _on_resume(s))
    extra_skills = sorted(resume_set - req_set - pref_set)

    breakdown = MatchBreakdown(
        skill_coverage=skill_coverage(matched_required, required) if required else skill_coverage(resume_profile.skills, required),
        tfidf_similarity=tfidf_cosine(
            resume_text,
            jd_text,
            extra_a=resume_profile.skills + matched_required,
            extra_b=required + preferred,
        ),
        experience_fit=experience_fit(resume_profile.experience.years, jd_profile.experience.years),
        education_fit=education_fit(resume_profile.education.level, jd_profile.education.level),
        preferred_bonus=preferred_bonus(matched_preferred, preferred),
    )
    score = weighted_score(breakdown, weights)
    return MatchResult(
        overall_score=round(score, 2),
        breakdown=breakdown,
        resume_profile=resume_profile,
        jd_profile=jd_profile,
        matched_required=matched_required,
        missing_required=missing_required,
        matched_preferred=matched_preferred,
        missing_preferred=missing_preferred,
        extra_skills=extra_skills,
        weights=weights,
    )


def rank_resumes(
    resumes: List[Dict[str, str]],
    jd_text: str,
    weights: Optional[Dict[str, float]] = None,
) -> List[Dict]:
    """Rank a list of {id, name, text} resumes against one job description."""
    jd_profile = extract_profile(jd_text, is_job_description=True)
    ranked = []
    for item in resumes:
        result = match_resume_to_jd(
            item["text"],
            jd_text,
            weights=weights,
            jd_profile=jd_profile,
        )
        ranked.append(
            {
                "id": item.get("id", ""),
                "name": item.get("name", item.get("id", "Candidate")),
                "score": result.overall_score,
                "matched_required": result.matched_required,
                "missing_required": result.missing_required,
                "years": result.resume_profile.experience.years,
                "degree": result.resume_profile.education.degree,
                "result": result,
            }
        )
    ranked.sort(key=lambda row: row["score"], reverse=True)
    for i, row in enumerate(ranked, start=1):
        row["rank"] = i
    return ranked
