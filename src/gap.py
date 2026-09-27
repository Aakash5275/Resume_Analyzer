"""Explainable gap analysis between a resume and a job description."""

from __future__ import annotations

from typing import Dict, List

from .match import MatchResult


IMPACT = {
    "critical": "Required for this role. Missing this skill is likely to block shortlisting.",
    "important": "Listed as required. Closing this gap would raise the match score.",
    "bonus": "Preferred, not mandatory. Having it would strengthen the profile.",
}


def _evidence_note(skill: str, mentions: Dict[str, List[str]]) -> str:
    forms = mentions.get(skill) or []
    if not forms:
        return "Detected from the skill taxonomy."
    shown = ", ".join(f"'{f}'" for f in forms[:3])
    return f"Matched from resume text: {shown}."


def build_gap_report(result: MatchResult) -> Dict:
    """Turn a match result into a recruiter-facing gap report."""
    resume_mentions = result.resume_profile.skill_mentions
    jd_mentions = result.jd_profile.skill_mentions

    missing_rows = []
    for skill in result.missing_required:
        missing_rows.append(
            {
                "skill": skill,
                "status": "Missing",
                "priority": "Required",
                "impact": IMPACT["critical"],
                "jd_evidence": ", ".join(jd_mentions.get(skill, [skill])[:3]),
            }
        )
    for skill in result.missing_preferred:
        missing_rows.append(
            {
                "skill": skill,
                "status": "Missing",
                "priority": "Preferred",
                "impact": IMPACT["bonus"],
                "jd_evidence": ", ".join(jd_mentions.get(skill, [skill])[:3]),
            }
        )

    matched_rows = []
    for skill in result.matched_required:
        matched_rows.append(
            {
                "skill": skill,
                "status": "Matched",
                "priority": "Required",
                "note": _evidence_note(skill, resume_mentions),
            }
        )
    for skill in result.matched_preferred:
        matched_rows.append(
            {
                "skill": skill,
                "status": "Matched",
                "priority": "Preferred",
                "note": _evidence_note(skill, resume_mentions),
            }
        )

    required_n = len(result.matched_required) + len(result.missing_required)
    coverage_pct = (
        round(100.0 * len(result.matched_required) / required_n, 1) if required_n else 100.0
    )

    suggestions = []
    if result.missing_required:
        top = ", ".join(result.missing_required[:5])
        suggestions.append(
            f"Add concrete project or work evidence for: {top}."
        )
    years = result.resume_profile.experience.years
    needed = result.jd_profile.experience.years
    if needed and (years is None or years < needed):
        have = "not stated" if years is None else f"{years:g} years"
        suggestions.append(
            f"The role asks for about {needed:g} years of experience; the resume shows {have}. "
            "Call out internships, freelance, or project duration more clearly."
        )
    if result.jd_profile.education.level and result.resume_profile.education.level < result.jd_profile.education.level:
        suggestions.append(
            "Education level is below the JD requirement. Mention equivalent coursework or certifications."
        )
    if not suggestions:
        suggestions.append("Strong overlap with the job description. Highlight leadership and impact metrics next.")

    verdict = _verdict(result.overall_score)
    return {
        "verdict": verdict,
        "overall_score": result.overall_score,
        "required_coverage_pct": coverage_pct,
        "missing_required": result.missing_required,
        "missing_preferred": result.missing_preferred,
        "matched_required": result.matched_required,
        "matched_preferred": result.matched_preferred,
        "extra_skills": result.extra_skills,
        "missing_rows": missing_rows,
        "matched_rows": matched_rows,
        "suggestions": suggestions,
        "experience": {
            "resume_years": result.resume_profile.experience.years,
            "jd_years": result.jd_profile.experience.years,
            "titles": result.resume_profile.experience.titles,
        },
        "education": {
            "resume_degree": result.resume_profile.education.degree,
            "resume_field": result.resume_profile.education.field_of_study,
            "resume_institution": result.resume_profile.education.institution,
            "jd_degree": result.jd_profile.education.degree,
        },
    }


def _verdict(score: float) -> str:
    if score >= 80:
        return "Strong fit"
    if score >= 65:
        return "Good fit"
    if score >= 45:
        return "Partial fit"
    return "Weak fit"
