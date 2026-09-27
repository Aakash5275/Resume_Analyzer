"""HTML preview and PDF export for photo and no-photo resume layouts."""

from __future__ import annotations

import base64
import html
import io
import re
from typing import Dict, Optional

from fpdf import FPDF
from fpdf.enums import XPos, YPos

PHOTO = "photo"
NO_PHOTO = "no_photo"

_BULLET = re.compile(r"^[\-•]\s+")


def _esc(text: str) -> str:
    return html.escape((text or "").strip())


def _initials(name: str) -> str:
    parts = [p for p in (name or "").split() if p]
    if not parts:
        return "FR"
    return "".join(p[0] for p in parts[:2]).upper()


def _photo_src(photo_bytes: Optional[bytes], mime: str = "image/jpeg") -> str:
    if not photo_bytes:
        return ""
    return f"data:{mime};base64,{base64.b64encode(photo_bytes).decode('ascii')}"


def _block_html(text: str) -> str:
    parts: list[str] = []
    bullets: list[str] = []

    def flush() -> None:
        if not bullets:
            return
        items = "".join(f"<li>{_esc(item)}</li>" for item in bullets)
        parts.append(f"<ul>{items}</ul>")
        bullets.clear()

    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line:
            flush()
            continue
        if _BULLET.match(line):
            bullets.append(_BULLET.sub("", line))
        else:
            flush()
            parts.append(f"<p>{_esc(line)}</p>")
    flush()
    return "".join(parts) or "<p></p>"


def _skill_pills(skills: str) -> str:
    items = [s.strip() for s in re.split(r"[,|\n]", skills or "") if s.strip()]
    if not items:
        return "<p class='muted'>Add skills</p>"
    return "".join(f"<span class='pill'>{_esc(item)}</span>" for item in items)


def render_html(doc: Dict[str, str], layout: str, photo_bytes: Optional[bytes] = None, photo_mime: str = "image/jpeg") -> str:
    name = _esc(doc.get("name") or "Your Name")
    title = _esc(doc.get("title") or "Target Role")
    email = _esc(doc.get("email") or "")
    phone = _esc(doc.get("phone") or "")
    location = _esc(doc.get("location") or "")
    summary = _esc(doc.get("summary") or "")
    experience = _block_html(doc.get("experience") or "")
    education = _block_html(doc.get("education") or "")
    projects = _block_html(doc.get("projects") or "")
    certs = _block_html(doc.get("certifications") or "")
    skills = _skill_pills(doc.get("skills") or "")
    src = _photo_src(photo_bytes, photo_mime)
    avatar = (
        f'<img class="avatar" src="{src}" alt="Profile photo">'
        if src
        else f'<div class="avatar fallback">{_esc(_initials(doc.get("name") or "FR"))}</div>'
    )
    css = """
    * { box-sizing: border-box; }
    body { margin: 0; background: #e8eef6; font-family: "Segoe UI", Arial, sans-serif; color: #1f2937; }
    .sheet { width: 794px; min-height: 1040px; margin: 0 auto; background: #fff; }
    h1,h2,h3,h4,p,ul { margin: 0; }
    ul { padding-left: 1.1rem; }
    li, p { font-size: 12.5px; line-height: 1.45; color: #334155; }
    .sec { font-size: 11px; letter-spacing: .08em; text-transform: uppercase; color: #2563eb; margin: 16px 0 8px; font-weight: 700; }
    .pill { display: inline-block; background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe;
            border-radius: 999px; padding: 3px 8px; margin: 0 6px 6px 0; font-size: 11px; font-weight: 650; }
    .muted { color: #94a3b8; }
    .photo { display: grid; grid-template-columns: 250px 1fr; min-height: 1040px; }
    .photo aside { background: #f8fafc; padding: 28px 22px; border-right: 1px solid #e5eaf1; }
    .photo main { padding: 32px 30px 28px; }
    .avatar { width: 118px; height: 118px; border-radius: 50%; object-fit: cover; display: block; margin: 0 auto 18px;
              border: 3px solid #2563eb; }
    .avatar.fallback { background: #2563eb; color: #fff; display: flex; align-items: center; justify-content: center;
                       font-weight: 800; font-size: 32px; }
    .photo h1 { font-size: 30px; letter-spacing: .04em; color: #0f172a; }
    .rule { height: 4px; width: 92px; background: #2563eb; margin: 8px 0 14px; border-radius: 99px; }
    .aside-title { font-size: 11px; letter-spacing: .1em; text-transform: uppercase; color: #2563eb; font-weight: 800; margin: 18px 0 7px; }
    .meta { font-size: 12px; color: #475569; line-height: 1.55; }
    .classic { padding: 34px 36px 30px; }
    .classic header { border-bottom: 2px solid #0f172a; padding-bottom: 12px; margin-bottom: 16px; }
    .classic h1 { font-size: 32px; letter-spacing: .08em; }
    .classic .role { color: #2563eb; font-weight: 650; margin-top: 4px; font-size: 14px; }
    .classic .topline { color: #64748b; font-size: 12px; margin-top: 6px; }
    .cols { display: grid; grid-template-columns: 1.35fr .9fr; gap: 28px; }
    """
    if layout == PHOTO:
        body = f"""
        <div class="sheet photo">
          <aside>
            {avatar}
            <div class="aside-title">Contact</div>
            <div class="meta">{phone}<br>{email}<br>{location}</div>
            <div class="aside-title">Education</div>
            {education}
            <div class="aside-title">Skills</div>
            {skills}
            <div class="aside-title">Certifications</div>
            {certs}
          </aside>
          <main>
            <h1>{name}</h1>
            <div class="rule"></div>
            <p style="color:#2563eb;font-weight:650;font-size:13px;margin-bottom:8px">{title}</p>
            <div class="sec">Professional summary</div>
            <p>{summary}</p>
            <div class="sec">Work history</div>
            {experience}
            <div class="sec">Projects</div>
            {projects}
          </main>
        </div>
        """
    else:
        body = f"""
        <div class="sheet classic">
          <header>
            <h1>{name}</h1>
            <p class="role">{title}</p>
            <p class="topline">{phone}  ·  {email}  ·  {location}</p>
          </header>
          <div class="cols">
            <div>
              <div class="sec">Summary</div>
              <p>{summary}</p>
              <div class="sec">Experience</div>
              {experience}
              <div class="sec">Education</div>
              {education}
            </div>
            <div>
              <div class="sec">Skills</div>
              {skills}
              <div class="sec">Projects</div>
              {projects}
              <div class="sec">Certifications</div>
              {certs}
            </div>
          </div>
        </div>
        """
    return f"<!doctype html><html><head><meta charset='utf-8'><style>{css}</style></head><body>{body}</body></html>"


class _ResumePDF(FPDF):
    def __init__(self, layout: str) -> None:
        super().__init__(format="A4", unit="mm")
        self.layout = layout
        self.set_auto_page_break(auto=True, margin=12)
        self.add_page()
        self.set_margins(12, 12, 12)


def _safe(text: str) -> str:
    return (text or "").replace("•", "-").replace("–", "-").replace("—", "-").encode("latin-1", "replace").decode("latin-1")


def _wrap(pdf: FPDF, x: float, width: float, text: str, line_h: float = 4.4) -> None:
    """Write wrapping text without leaving the cursor at the right edge."""
    usable = max(width, 20)
    content = _safe(text) or " "
    pdf.set_x(x)
    pdf.multi_cell(usable, line_h, content, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_x(x)


def _write_wrapped(pdf: FPDF, x: float, text: str, width: float, size: int = 9) -> None:
    pdf.set_font("Helvetica", size=size)
    pdf.set_text_color(51, 65, 85)
    for raw in (text or "").splitlines() or [" "]:
        line = raw.strip()
        if not line:
            pdf.ln(2)
            pdf.set_x(x)
            continue
        if _BULLET.match(line):
            line = "- " + _BULLET.sub("", line)
        _wrap(pdf, x, width, line)


def _heading(pdf: FPDF, x: float, label: str, width: float) -> None:
    pdf.ln(3)
    pdf.set_x(x)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(37, 99, 235)
    pdf.cell(max(width, 20), 6, _safe(label.upper()), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_x(x)


def render_pdf(doc: Dict[str, str], layout: str, photo_bytes: Optional[bytes] = None) -> bytes:
    pdf = _ResumePDF(layout)
    name = _safe(doc.get("name") or "Your Name")
    title = _safe(doc.get("title") or "Target Role")
    email = _safe(doc.get("email") or "")
    phone = _safe(doc.get("phone") or "")
    location = _safe(doc.get("location") or "")
    summary = _safe(doc.get("summary") or "")
    skills = _safe(doc.get("skills") or "")
    experience = doc.get("experience") or ""
    education = doc.get("education") or ""
    projects = doc.get("projects") or ""
    certs = doc.get("certifications") or ""

    if layout == PHOTO:
        sidebar_w = 62
        pdf.set_fill_color(248, 250, 252)
        pdf.rect(0, 0, sidebar_w, 297, "F")
        x = 8
        if photo_bytes:
            try:
                pdf.image(io.BytesIO(photo_bytes), x=16, y=14, w=30, h=30)
            except Exception:
                photo_bytes = None
        if not photo_bytes:
            pdf.set_fill_color(37, 99, 235)
            pdf.ellipse(16, 14, 30, 30, "F")
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Helvetica", "B", 14)
            pdf.set_xy(16, 24)
            pdf.cell(30, 8, _safe(_initials(doc.get("name") or "FR")), align="C")

        pdf.set_xy(x, 50)
        side_w = sidebar_w - 14
        _heading(pdf, x, "Contact", side_w)
        _write_wrapped(pdf, x, f"{phone}\n{email}\n{location}", side_w, 8)
        _heading(pdf, x, "Education", side_w)
        _write_wrapped(pdf, x, education, side_w, 8)
        _heading(pdf, x, "Skills", side_w)
        _write_wrapped(pdf, x, skills, side_w, 8)
        if certs.strip():
            _heading(pdf, x, "Certifications", side_w)
            _write_wrapped(pdf, x, certs, side_w, 8)

        left = 72
        width = 126
        pdf.set_xy(left, 16)
        pdf.set_font("Helvetica", "B", 20)
        pdf.set_text_color(15, 23, 42)
        _wrap(pdf, left, width, name, 8)
        pdf.set_fill_color(37, 99, 235)
        pdf.rect(left, pdf.get_y(), 22, 1.4, "F")
        pdf.ln(6)
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(37, 99, 235)
        _wrap(pdf, left, width, title, 6)
        _heading(pdf, left, "Professional summary", width)
        _write_wrapped(pdf, left, summary, width)
        _heading(pdf, left, "Work history", width)
        _write_wrapped(pdf, left, experience, width)
        if projects.strip():
            _heading(pdf, left, "Projects", width)
            _write_wrapped(pdf, left, projects, width)
    else:
        left = 12
        full = 186
        pdf.set_xy(left, 12)
        pdf.set_font("Helvetica", "B", 22)
        pdf.set_text_color(15, 23, 42)
        _wrap(pdf, left, full, name, 9)
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(37, 99, 235)
        _wrap(pdf, left, full, title, 6)
        pdf.set_font("Helvetica", size=9)
        pdf.set_text_color(100, 116, 139)
        _wrap(pdf, left, full, f"{phone}  |  {email}  |  {location}", 5)
        pdf.ln(2)
        pdf.set_draw_color(15, 23, 42)
        pdf.line(12, pdf.get_y(), 198, pdf.get_y())
        pdf.ln(6)
        y0 = pdf.get_y()
        col_w = 110
        right_x = 130
        right_w = 66
        pdf.set_xy(left, y0)
        _heading(pdf, left, "Summary", col_w)
        _write_wrapped(pdf, left, summary, col_w)
        _heading(pdf, left, "Experience", col_w)
        _write_wrapped(pdf, left, experience, col_w)
        _heading(pdf, left, "Education", col_w)
        _write_wrapped(pdf, left, education, col_w)
        left_end = pdf.get_y()
        pdf.set_xy(right_x, y0)
        _heading(pdf, right_x, "Skills", right_w)
        _write_wrapped(pdf, right_x, skills, right_w)
        _heading(pdf, right_x, "Projects", right_w)
        _write_wrapped(pdf, right_x, projects, right_w)
        if certs.strip():
            _heading(pdf, right_x, "Certifications", right_w)
            _write_wrapped(pdf, right_x, certs, right_w)
        pdf.set_y(max(left_end, pdf.get_y()) + 4)

    return bytes(pdf.output())
