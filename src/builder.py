"""Build a JD-tailored resume draft from extracted requirements."""

from __future__ import annotations

import re
from typing import Dict, List

from .extract import extract_profile
from .preprocess import normalize_unicode

SECTION_RE = re.compile(
    r"^(summary|profile|objective|experience|work history|employment|"
    r"education|skills|projects|certifications)\b",
    re.IGNORECASE,
)
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
PHONE_RE = re.compile(r"(\+?\d[\d\s().-]{7,}\d)")


def _split_sections(text: str) -> Dict[str, str]:
    blocks: Dict[str, List[str]] = {}
    current = "body"
    for raw in normalize_unicode(text or "").splitlines():
        line = raw.strip()
        if not line:
            if current in blocks:
                blocks[current].append("")
            continue
        heading = SECTION_RE.match(line.rstrip(":"))
        if heading and len(line) < 48:
            current = heading.group(1).lower()
            blocks.setdefault(current, [])
            continue
        blocks.setdefault(current, []).append(raw.rstrip())
    return {key: "\n".join(val).strip() for key, val in blocks.items() if "".join(val).strip()}


def _first_name(text: str, fallback: str) -> str:
    if fallback.strip():
        return fallback.strip()
    for line in (text or "").splitlines():
        clean = line.strip()
        if 2 <= len(clean.split()) <= 4 and len(clean) < 48 and not SECTION_RE.match(clean):
            if re.search(r"[A-Za-z]", clean) and "@" not in clean:
                return clean
    return "Your Name"


def _join(items: List[str], empty: str = "Add relevant skills from your background") -> str:
    return ", ".join(items) if items else empty


def _split_contact(contact: str, source: str) -> Dict[str, str]:
    blob = f"{contact}\n{source}"
    email_match = EMAIL_RE.search(blob)
    phone_match = PHONE_RE.search(blob)
    location = ""
    if contact and "|" in contact:
        parts = [p.strip() for p in contact.split("|") if p.strip()]
        leftover = [p for p in parts if "@" not in p and not PHONE_RE.search(p)]
        location = leftover[0] if leftover else ""
    return {
        "email": email_match.group(0) if email_match else "",
        "phone": phone_match.group(0).strip() if phone_match else "",
        "location": location,
    }


def build_resume(
    jd_text: str,
    source_resume: str = "",
    name: str = "",
    contact: str = "",
    target_title: str = "",
) -> Dict:
    """Return a tailored resume draft and the JD skills that shaped it."""
    jd = extract_profile(jd_text, is_job_description=True)
    required = jd.required_skills or jd.skills
    preferred = jd.preferred_skills
    source = (source_resume or "").strip()
    profile = extract_profile(source) if source else None
    sections = _split_sections(source) if source else {}

    have = set(profile.skills) if profile else set()
    matched = [s for s in required if s in have]
    extra = sorted(have - set(required) - set(preferred))
    missing_required = [s for s in required if s not in have]
    missing_preferred = [s for s in preferred if s not in have]
    highlight = matched + [s for s in preferred if s in have] + extra

    role = target_title.strip() or (jd.experience.titles[0] if jd.experience.titles else "Target Role")
    years = None
    if profile and profile.experience.years:
        years = profile.experience.years
    elif jd.experience.years:
        years = jd.experience.years

    display_name = _first_name(source, name)
    bits = _split_contact(contact, source)
    contact_line = contact.strip() or " | ".join(p for p in [bits["email"], bits["phone"], bits["location"]] if p) or "email@example.com | phone | city"

    if years:
        summary = (
            f"{display_name.split()[0]} is a {role} with about {years:g} years of experience, "
            f"focused on {', '.join((matched or required)[:4]) or 'the core requirements of this role'}."
        )
    else:
        summary = (
            f"Results-oriented {role} aligned to this opening, with strengths in "
            f"{', '.join((matched or required)[:5]) or 'the listed job requirements'}."
        )
    if source and sections.get("summary"):
        summary = sections["summary"].split("\n")[0][:360]

    edu_bits = []
    if profile and profile.education.degree:
        edu_bits.append(profile.education.degree)
    if profile and profile.education.field_of_study:
        edu_bits.append(profile.education.field_of_study)
    if profile and profile.education.institution:
        edu_bits.append(profile.education.institution)
    education = (
        sections.get("education")
        or (", ".join(edu_bits) if edu_bits else "Degree, Field, Institution")
    )

    experience = (
        sections.get("experience")
        or sections.get("work history")
        or sections.get("employment")
        or sections.get("body")
    )
    if not experience and profile and profile.experience.titles:
        experience = "\n".join(f"- {title}" for title in profile.experience.titles[:6])
    if not experience:
        experience = (
            "Role Title  |  Company  |  Dates\n"
            "- Describe an achievement that uses a required skill from the job description.\n"
            "- Quantify impact (time saved, revenue, quality, users).\n"
            "- Mention tools from the Skills section above."
        )

    projects = sections.get("projects")
    if not projects and missing_required[:3]:
        projects = (
            "Project title  |  tools: "
            + ", ".join(missing_required[:3])
            + "\n- Brief outcome that shows you can apply a skill the job asks for."
        )

    certifications = sections.get("certifications") or ""
    skills_text = _join(highlight or required)

    draft_lines = [
        display_name,
        contact_line,
        "",
        "TARGET ROLE",
        role,
        "",
        "PROFESSIONAL SUMMARY",
        summary,
        "",
        "SKILLS",
        skills_text,
        "",
        "EXPERIENCE",
        experience,
        "",
        "EDUCATION",
        education,
    ]
    if projects:
        draft_lines.extend(["", "PROJECTS", projects])
    if missing_required:
        draft_lines.extend(
            [
                "",
                "OPTIONAL ADDITIONS (only if true for you)",
                "The job also asks for: " + ", ".join(missing_required[:8]) + ".",
            ]
        )

    doc = {
        "name": display_name,
        "title": role,
        "email": bits["email"] or "email@example.com",
        "phone": bits["phone"] or "phone",
        "location": bits["location"] or "city",
        "summary": summary,
        "skills": skills_text,
        "experience": experience,
        "education": education,
        "projects": projects or "",
        "certifications": certifications,
    }

    return {
        "draft": "\n".join(draft_lines).strip() + "\n",
        "doc": doc,
        "role": role,
        "required_skills": required,
        "preferred_skills": preferred,
        "matched_skills": matched,
        "missing_required": missing_required,
        "missing_preferred": missing_preferred,
        "used_source_resume": bool(source),
    }


def ensure_doc(built: Dict) -> Dict[str, str]:
    """Use the structured doc, or rebuild it from an older draft-only result."""
    if built.get("doc"):
        return built["doc"]
    draft = built.get("draft") or ""
    lines = [line.strip() for line in draft.splitlines() if line.strip()]
    sections: Dict[str, List[str]] = {}
    current = "body"
    for line in lines:
        key = line.lower()
        if key in {
            "target role",
            "professional summary",
            "skills",
            "experience",
            "education",
            "projects",
            "certifications",
        }:
            current = key
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(line)
    body = sections.get("body") or []
    contact = body[1] if len(body) > 1 else ""
    bits = _split_contact(contact, "")
    doc = {
        "name": body[0] if body else "Your Name",
        "title": " ".join(sections.get("target role") or [built.get("role") or "Target Role"]),
        "email": bits["email"] or "email@example.com",
        "phone": bits["phone"] or "phone",
        "location": bits["location"] or "city",
        "summary": " ".join(sections.get("professional summary") or []),
        "skills": ", ".join(sections.get("skills") or built.get("matched_skills") or []),
        "experience": "\n".join(sections.get("experience") or []),
        "education": "\n".join(sections.get("education") or []),
        "projects": "\n".join(sections.get("projects") or []),
        "certifications": "\n".join(sections.get("certifications") or []),
    }
    built["doc"] = doc
    return doc
