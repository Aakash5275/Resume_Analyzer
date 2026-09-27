"""Information extraction from unstructured resume and JD text.

Skills are extracted with a longest-match gazetteer plus fuzzy fallback.
Experience years, job titles, degrees, and institutions use regular
expressions over the original (lightly normalized) text so that numbers
and proper names are not destroyed by stopword filtering.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from dataclasses import field as data_field
from functools import lru_cache
from typing import Dict, List, Optional, Set, Tuple

from rapidfuzz import process

from .preprocess import normalize_unicode, sentences
from .skills_taxonomy import (
    BODY_SECTION_CUES,
    PREFERRED_SECTION_CUES,
    REQUIRED_SECTION_CUES,
    SKILL_GROUPS,
    build_alias_map,
)

_ALIAS_TO_CANONICAL, _LOOKUP_TERMS = build_alias_map()

# Terms that are too short / ambiguous unless they appear as standalone tokens.
_STRICT_STANDALONE = {
    "c", "r", "go", "js", "ts", "ml", "dl", "cv", "ir", "tf", "k8s",
    "qa", "ap", "ar", "rn", "cad",
}
# English words that also appear as skill aliases — only keep them in list-like lines.
_AMBIGUOUS_TERMS = {
    "go", "rest", "node", "spring", "express", "c", "r", "cad", "ir", "cv",
    "ml", "qa", "ap", "ar", "rn", "js", "ts", "tf",
}

YEARS_RE = re.compile(
    r"(?P<years>\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)\s+(?:of\s+)?(?:experience|exp)",
    re.IGNORECASE,
)
YEARS_ALT_RE = re.compile(
    r"(?:experience|exp)[^\d]{0,20}(?P<years>\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)",
    re.IGNORECASE,
)
RANGE_RE = re.compile(
    r"\b(20\d{2}|19\d{2})\s*[-–—to]{1,3}\s*(20\d{2}|19\d{2}|present|current|now)\b",
    re.IGNORECASE,
)

DEGREE_PATTERNS: List[Tuple[str, str, int]] = [
    (r"\bph\.?d\.?\b|doctor of philosophy|doctorate", "PhD", 4),
    (r"\bm\.?\s*tech\b|\bm\.?\s*e\.?\b|master of technology|mtech", "M.Tech", 3),
    (r"\bm\.?\s*s\.?\b|master of science|\bmsc\b|masters?\b", "M.S.", 3),
    (r"\bmba\b|master of business", "MBA", 3),
    (r"\bb\.?\s*tech\b|\bb\.?\s*e\.?\b|bachelor of technology|btech", "B.Tech", 2),
    (r"\bb\.?\s*s\.?\b|bachelor of science|\bbsc\b|bachelors?\b", "B.S.", 2),
    (r"\bb\.?\s*a\.?\b|bachelor of arts|\bba\b", "B.A.", 2),
    (r"\bbca\b|bachelor of computer applications", "BCA", 2),
    (r"\bmca\b|master of computer applications", "MCA", 3),
]

FIELD_RE = re.compile(
    r"(?:in|of)\s+(computer science|information technology|electronics|"
    r"electrical|mechanical|data science|artificial intelligence|"
    r"machine learning|statistics|mathematics|physics|business administration)"
    r"(?:\s+and\s+\w+)?",
    re.IGNORECASE,
)

INSTITUTION_RE = re.compile(
    r"\b(?:university|institute|college|iit|nit|iiit|mit|stanford|harvard|"
    r"berkeley|cmu|georgia tech|bits)\b[^,\n]{0,60}",
    re.IGNORECASE,
)

TITLE_CUES = (
    "engineer", "developer", "scientist", "analyst", "manager", "intern",
    "architect", "specialist", "consultant", "lead", "head", "director",
    "researcher", "administrator", "designer",
)


@dataclass
class Education:
    degree: Optional[str] = None
    level: int = 0
    field_of_study: Optional[str] = None
    institution: Optional[str] = None
    raw_mentions: List[str] = data_field(default_factory=list)


@dataclass
class Experience:
    years: Optional[float] = None
    titles: List[str] = data_field(default_factory=list)
    date_spans: List[str] = data_field(default_factory=list)


@dataclass
class ExtractedProfile:
    skills: List[str] = data_field(default_factory=list)
    skill_mentions: Dict[str, List[str]] = data_field(default_factory=dict)
    experience: Experience = data_field(default_factory=Experience)
    education: Education = data_field(default_factory=Education)
    required_skills: List[str] = data_field(default_factory=list)
    preferred_skills: List[str] = data_field(default_factory=list)


def _skill_haystack(text: str) -> str:
    """Lowercase text, keep line breaks, turn slashes into spaces for matching."""
    raw = normalize_unicode(text or "").lower()
    raw = raw.replace("\u2022", "\n").replace("•", "\n")
    raw = raw.replace("/", " ").replace("\\", " ").replace("|", " ")
    raw = re.sub(r"[ \t]+", " ", raw)
    return raw


def _token_windows(text: str) -> str:
    return re.sub(r"\s+", " ", _skill_haystack(text))


def _line_at(haystack: str, start: int, end: int) -> str:
    left = haystack.rfind("\n", 0, start) + 1
    right = haystack.find("\n", end)
    return haystack[left : right if right >= 0 else None].strip()


def _is_list_context(haystack: str, start: int, end: int) -> bool:
    line = _line_at(haystack, start, end)
    if not line:
        return False
    if line[:1] in {"-", "*", "•"} or re.match(r"^\d+[.)]\s", line):
        return True
    if "," in line or ";" in line:
        return True
    return bool(
        re.search(
            r"\b(python|java|javascript|typescript|sql|aws|azure|react|docker|"
            r"kubernetes|skill|stack|framework|developer|engineer|languages?)\b",
            line,
        )
    )


def _is_standalone_match(haystack: str, start: int, end: int, term: str) -> bool:
    left_ok = start == 0 or not haystack[start - 1].isalnum()
    right_ok = end >= len(haystack) or not haystack[end].isalnum()
    if not (left_ok and right_ok):
        return False
    if term in _AMBIGUOUS_TERMS and not _is_list_context(haystack, start, end):
        return False
    return True


NEGATION_RE = re.compile(
    r"\b(?:no|not|without|lacking|lack of|don't|do not|does not|didn't)\b",
    re.IGNORECASE,
)


def _is_negated(haystack: str, start: int, window: int = 48) -> bool:
    left = haystack[max(0, start - window) : start]
    return bool(NEGATION_RE.search(left))


def extract_skills(text: str, fuzzy_threshold: int = 92) -> Tuple[List[str], Dict[str, List[str]]]:
    """Return canonical skills and the surface forms that triggered each one."""
    haystack = _skill_haystack(text)
    found: Dict[str, Set[str]] = {}
    occupied = [False] * len(haystack)

    for term in _LOOKUP_TERMS:
        start = 0
        while True:
            idx = haystack.find(term, start)
            if idx < 0:
                break
            end = idx + len(term)
            if (
                _is_standalone_match(haystack, idx, end, term)
                and not _is_negated(haystack, idx)
                and not any(occupied[idx:end])
            ):
                canonical = _ALIAS_TO_CANONICAL[term]
                found.setdefault(canonical, set()).add(term)
                for i in range(idx, end):
                    occupied[i] = True
                start = end
            else:
                start = idx + 1

    if fuzzy_threshold:
        unmatched_terms = {
            term: canon
            for term, canon in _ALIAS_TO_CANONICAL.items()
            if canon not in found and len(term) >= 8 and " " in term
        }
        tokens = haystack.split()
        grams = []
        for n in (2, 3):
            for i in range(len(tokens) - n + 1):
                grams.append(" ".join(tokens[i : i + n]))
        if grams and unmatched_terms:
            unique_grams = list(dict.fromkeys(grams))
            for term, canon in unmatched_terms.items():
                if term in haystack:
                    continue
                hit = process.extractOne(term, unique_grams, score_cutoff=fuzzy_threshold)
                if hit:
                    found.setdefault(canon, set()).add(hit[0])

    skills = sorted(found.keys())
    mentions = {k: sorted(v) for k, v in found.items()}
    return skills, mentions


def terms_for_skill(canonical: str) -> List[str]:
    aliases = SKILL_GROUPS.get(canonical, [])
    forms = {canonical.lower(), *[a.lower() for a in aliases]}
    return sorted(forms, key=len, reverse=True)


def text_has_skill(text: str, canonical: str) -> bool:
    """True if the resume/JD text mentions a skill or one of its aliases."""
    haystack = _skill_haystack(text)
    collapsed = re.sub(r"\s+", " ", haystack)
    for term in terms_for_skill(canonical):
        spaced = term.replace("/", " ")
        for hay in (haystack, collapsed):
            start = 0
            while True:
                idx = hay.find(spaced, start)
                if idx < 0:
                    break
                end = idx + len(spaced)
                if _is_standalone_match(hay, idx, end, term) and not _is_negated(hay, idx):
                    return True
                start = idx + 1
    return False


def extract_experience(text: str) -> Experience:
    years: List[float] = []
    for pattern in (YEARS_RE, YEARS_ALT_RE):
        for match in pattern.finditer(text or ""):
            try:
                years.append(float(match.group("years")))
            except (TypeError, ValueError):
                continue

    spans = [m.group(0) for m in RANGE_RE.finditer(text or "")]
    if not years and spans:
        total = 0.0
        for span in spans:
            parts = re.split(r"[-–—]|to", span, flags=re.IGNORECASE)
            if len(parts) != 2:
                continue
            start = parts[0].strip()
            end = parts[1].strip().lower()
            try:
                start_y = int(re.sub(r"\D", "", start)[:4])
                end_y = 2026 if end in {"present", "current", "now"} else int(re.sub(r"\D", "", end)[:4])
                if 0 <= end_y - start_y <= 40:
                    total += end_y - start_y
            except ValueError:
                continue
        if total:
            years.append(total)

    titles: List[str] = []
    for sent in sentences(text):
        lower = sent.lower()
        if any(cue in lower for cue in TITLE_CUES) and len(sent) < 140:
            cleaned = re.sub(r"\s+", " ", sent).strip(" -•|\t")
            if cleaned and cleaned not in titles:
                titles.append(cleaned)
            if len(titles) >= 8:
                break

    return Experience(
        years=max(years) if years else None,
        titles=titles[:8],
        date_spans=spans[:8],
    )


def extract_education(text: str) -> Education:
    best_degree: Optional[str] = None
    best_level = 0
    mentions: List[str] = []
    raw = text or ""
    for pattern, label, level in DEGREE_PATTERNS:
        if re.search(pattern, raw, flags=re.IGNORECASE):
            mentions.append(label)
            if level > best_level:
                best_level = level
                best_degree = label

    field_of_study = None
    field_match = FIELD_RE.search(raw)
    if field_match:
        field_of_study = field_match.group(1).title()

    institution = None
    inst_match = INSTITUTION_RE.search(raw)
    if inst_match:
        institution = re.sub(r"\s+", " ", inst_match.group(0)).strip(" ,.;")

    return Education(
        degree=best_degree,
        level=best_level,
        field_of_study=field_of_study,
        institution=institution,
        raw_mentions=list(dict.fromkeys(mentions)),
    )


def _is_section_heading(line: str, cues: tuple[str, ...]) -> bool:
    lowered = line.strip().lower().strip(":-")
    if not lowered or len(lowered) > 70:
        return False
    if lowered[:1] in {"-", "•", "*", "–"}:
        return False
    return any(lowered == cue or lowered.startswith(cue + " ") for cue in cues)


def _split_jd_sections(text: str) -> Tuple[str, str, str]:
    """Return (full, required_block, preferred_block)."""
    raw = normalize_unicode(text or "")
    lines = raw.splitlines()
    required_lines: List[str] = []
    preferred_lines: List[str] = []
    current = "full"
    for line in lines:
        if _is_section_heading(line, PREFERRED_SECTION_CUES):
            current = "preferred"
            continue
        if _is_section_heading(line, REQUIRED_SECTION_CUES):
            current = "required"
            continue
        if _is_section_heading(line, BODY_SECTION_CUES):
            current = "full"
            continue
        if current == "required":
            required_lines.append(line)
        elif current == "preferred":
            preferred_lines.append(line)
    return raw, "\n".join(required_lines), "\n".join(preferred_lines)


@lru_cache(maxsize=128)
def extract_profile(text: str, is_job_description: bool = False) -> ExtractedProfile:
    skills, mentions = extract_skills(text)
    experience = extract_experience(text)
    education = extract_education(text)
    required: List[str] = []
    preferred: List[str] = []
    if is_job_description:
        _, _req_block, pref_block = _split_jd_sections(text)
        if pref_block.strip():
            preferred, _ = extract_skills(pref_block)
        # All JD skills are in scope; preferred-section skills stay preferred only.
        required = [s for s in skills if s not in set(preferred)]
        if not required:
            required = list(skills)
        preferred = [s for s in preferred if s not in set(required)]
    return ExtractedProfile(
        skills=skills,
        skill_mentions=mentions,
        experience=experience,
        education=education,
        required_skills=required,
        preferred_skills=preferred,
    )
