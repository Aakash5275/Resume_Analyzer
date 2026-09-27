"""Professional light-theme UI: screen a resume or build one from a JD."""

from __future__ import annotations

import html
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from src.builder import build_resume, ensure_doc
from src.io_utils import load_uploaded_file
from src.pipeline import screen
from src.resume_format import NO_PHOTO, PHOTO, render_html, render_pdf

PAGES = ("Screen", "Resume builder")

st.set_page_config(
    page_title="FitRank · Resume Screener",
    page_icon="FR",
    layout="wide",
    initial_sidebar_state="expanded",
)

CSS = """
<style>
@import url("https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,700&family=Outfit:wght@400;500;600;700&display=swap");

html { font-size: 17px; }
html, body, [class*="css"], .stApp, .stMarkdown, .stText, p, label, input, textarea, button {
    font-family: "Outfit", "Segoe UI", sans-serif;
}
.stApp {
    overflow-x: hidden;
    background:
        radial-gradient(920px 460px at -8% -12%, #dbe7ff 0%, transparent 58%),
        radial-gradient(720px 380px at 108% -4%, #cffafe 0%, transparent 52%),
        radial-gradient(640px 280px at 70% 110%, #e0e7ff 0%, transparent 48%),
        #f5f7fb;
}
[data-testid="stHeader"] { background: transparent; }
[data-testid="stToolbar"] { visibility: hidden; }
[data-testid="stSidebarCollapsedControl"] { visibility: visible !important; display: flex !important; }
footer, #MainMenu { visibility: hidden; }
[data-testid="stMain"] { overflow-x: hidden; }

[data-testid="stSidebar"] {
    background: rgba(255,255,255,0.88);
    backdrop-filter: blur(16px);
    border-right: 1px solid #e4e9f2;
}
[data-testid="stSidebar"] > div:first-child { padding: 1.25rem 1.05rem 1.6rem; }

.brand {
    display: flex; align-items: center; gap: 12px;
    margin-bottom: 1.15rem; padding: 2px 2px 18px;
    border-bottom: 1px solid #e8edf5;
}
.brand-mark {
    width: 44px; height: 44px; border-radius: 13px;
    background: linear-gradient(145deg, #1d4ed8 0%, #38bdf8 100%);
    color: #fff; display: flex; align-items: center; justify-content: center;
    font-weight: 700; letter-spacing: 0.02em; font-size: 1rem;
    box-shadow: 0 10px 22px rgba(29, 78, 216, 0.28);
}
.brand h2 { margin: 0; font-size: 1.2rem; color: #0f172a; font-weight: 700; }
.brand p { margin: 3px 0 0; color: #64748b; font-size: 0.86rem; }

.side-note {
    background: #f8fbff; border: 1px solid #e0e9f6; border-radius: 14px;
    padding: 12px 13px; color: #475569; font-size: 0.92rem; line-height: 1.45;
}

.hero {
    position: relative; overflow: hidden;
    background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
    border: 1px solid #e4ebf5;
    border-radius: 22px;
    padding: 1.55rem 1.7rem 1.4rem;
    margin-bottom: 1.2rem;
    box-shadow: 0 16px 40px rgba(15, 23, 42, 0.05);
}
.hero::after {
    content: "";
    position: absolute; right: -40px; top: -50px;
    width: 180px; height: 180px; border-radius: 50%;
    background: radial-gradient(circle, rgba(56,189,248,0.18), transparent 70%);
}
.kicker {
    display: inline-block; margin: 0 0 .55rem;
    padding: .22rem .65rem; border-radius: 999px;
    background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe;
    font-size: 0.78rem; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase;
}
.hero h1 {
    margin: 0 0 .45rem; font-family: "Fraunces", Georgia, serif;
    font-size: 2.15rem; font-weight: 700; color: #0f172a;
    letter-spacing: -0.03em; line-height: 1.15;
}
.hero p { margin: 0; color: #64748b; font-size: 1.08rem; line-height: 1.55; max-width: 46rem; }
.hero-steps { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 1rem; }
.step {
    background: #fff; border: 1px solid #e2e8f0; color: #334155;
    border-radius: 999px; padding: .38rem .8rem;
    font-size: 0.92rem; font-weight: 600;
}
.step b { color: #2563eb; margin-right: 4px; }

.panel-label {
    font-size: 0.8rem; font-weight: 700; letter-spacing: 0.08em;
    text-transform: uppercase; color: #64748b; margin: 0 0 .65rem;
}
.card-head {
    display: flex; align-items: center; gap: 10px; margin: 0 0 .75rem;
}
.card-ico {
    width: 34px; height: 34px; border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.95rem; font-weight: 700; flex-shrink: 0;
}
.ico-blue { background: #eff6ff; color: #1d4ed8; }
.ico-teal { background: #ecfeff; color: #0e7490; }
.ico-green { background: #ecfdf3; color: #067647; }
.ico-rose { background: #fef3f2; color: #b42318; }
.card-head h3 { margin: 0; font-size: 1.08rem; color: #0f172a; font-weight: 650; }
.card-head span { display: block; color: #94a3b8; font-size: 0.86rem; font-weight: 500; }

.chip {
    display: inline-block; padding: .36rem .76rem; border-radius: 999px;
    margin: .16rem .18rem .16rem 0; font-size: .88rem; font-weight: 650;
    border: 1px solid transparent;
}
.chip-ok { background: #ecfdf3; color: #067647; border-color: #abefc6; }
.chip-miss { background: #fef3f2; color: #b42318; border-color: #fecdca; }
.chip-pref { background: #fffaeb; color: #b54708; border-color: #fedf89; }
.chip-extra { background: #eef4ff; color: #3538cd; border-color: #c7d7fe; }
.muted { color: #94a3b8; font-size: 1rem; }

.score-hero {
    display: flex; align-items: center; gap: 1.1rem;
    background: linear-gradient(180deg, #ffffff, #f7faff);
    border: 1px solid #e4ebf5; border-radius: 20px;
    padding: 1.15rem 1.25rem; margin: .2rem 0 1rem;
    box-shadow: 0 12px 30px rgba(15, 23, 42, 0.05);
}
.ring {
    width: 108px; height: 108px; border-radius: 50%; flex-shrink: 0;
    display: grid; place-items: center;
    box-shadow: inset 0 0 0 1px #e8edf5;
}
.ring-inner {
    width: 82px; height: 82px; border-radius: 50%;
    background: #fff; display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    box-shadow: 0 6px 16px rgba(15, 23, 42, 0.06);
}
.ring-inner strong {
    font-family: "Fraunces", Georgia, serif;
    font-size: 1.55rem; line-height: 1; color: #0f172a;
}
.ring-inner small { color: #94a3b8; font-size: 0.72rem; font-weight: 650; margin-top: 3px; }
.score-copy { min-width: 0; }
.score-copy .label { color: #64748b; font-size: 0.86rem; font-weight: 650; letter-spacing: 0.04em; text-transform: uppercase; }
.score-verdict { font-size: 1.28rem; font-weight: 700; margin-top: .2rem; }
.v-strong { color: #067647; }
.v-good { color: #175cd3; }
.v-partial { color: #b54708; }
.v-weak { color: #b42318; }

.empty {
    background: #fff; border: 1px dashed #cbd5e1; border-radius: 20px;
    padding: 2rem 1.4rem; text-align: center; color: #64748b; margin-top: .55rem;
    font-size: 1.05rem; line-height: 1.55;
    box-shadow: 0 10px 28px rgba(15, 23, 42, 0.03);
}
.empty .mark {
    width: 52px; height: 52px; border-radius: 16px; margin: 0 auto .75rem;
    background: linear-gradient(145deg, #eff6ff, #ecfeff);
    color: #2563eb; display: flex; align-items: center; justify-content: center;
    font-weight: 800; font-size: 1.15rem;
}
.empty strong { display: block; color: #0f172a; font-size: 1.2rem; margin-bottom: .35rem; font-family: "Fraunces", Georgia, serif; }

.tip {
    background: #f8fbff; border: 1px solid #e4ebf5; border-radius: 12px;
    padding: 10px 13px; margin: 0 0 8px; color: #334155; font-size: 1.02rem;
}

div[data-testid="stMetric"] {
    background: #ffffff; border: 1px solid #e4ebf5; border-radius: 16px;
    padding: 14px 16px; box-shadow: 0 8px 20px rgba(15, 23, 42, 0.035);
}
div[data-testid="stMetric"] label { color: #64748b !important; font-size: 0.9rem !important; }
div[data-testid="stMetricValue"] { color: #0f172a; font-size: 1.4rem !important; }

[data-testid="stVerticalBlockBorderWrapper"] {
    background: #fff !important;
    border: 1px solid #e4ebf5 !important;
    border-radius: 20px !important;
    box-shadow: 0 12px 30px rgba(15, 23, 42, 0.04);
    padding: 4px;
}

.nav-bar { margin: 0 0 1rem; }
.format-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.format-card {
    border: 1px solid #e4ebf5; border-radius: 16px; padding: 12px; background: #f8fbff;
}
.format-card strong { display: block; color: #0f172a; margin-bottom: 8px; font-size: 0.98rem; }
.mock { height: 92px; border-radius: 10px; background: #fff; border: 1px solid #e5eaf1; display: grid; overflow: hidden; }
.mock-photo { grid-template-columns: 34px 1fr; }
.mock-photo .s { background: #e2e8f0; }
.mock-photo .m, .mock-plain .m { padding: 8px; }
.mock-plain { padding: 8px; }
.bar { height: 6px; background: #cbd5e1; border-radius: 99px; margin-bottom: 6px; }
.bar.short { width: 42%; background: #2563eb; }
.preview-wrap { background: #e8eef6; border-radius: 16px; padding: 10px; overflow: auto; }

label, [data-testid="stWidgetLabel"] p, [data-testid="stMarkdownContainer"] p {
    font-size: 1.02rem !important; line-height: 1.5;
}
.stButton > button {
    min-height: 50px; border-radius: 13px; font-weight: 700;
    font-size: 1.05rem !important; border: 0 !important;
}
button[kind="primary"], .stButton > button[data-testid="stBaseButton-primary"] {
    background: linear-gradient(135deg, #1d4ed8, #2563eb) !important;
    color: #fff !important;
    box-shadow: 0 10px 22px rgba(37, 99, 235, 0.28);
}
.stTextInput input, .stTextArea textarea {
    border-radius: 12px !important;
    border-color: #d7dee8 !important;
    background: #fcfdff !important;
    font-size: 1.04rem !important;
    line-height: 1.5 !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: #93c5fd !important;
    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12) !important;
}
[data-testid="stFileUploader"] { margin-bottom: .35rem; }
[data-testid="stFileUploader"] section {
    min-height: 78px;
    background: #f8fbff !important;
    border: 1.5px dashed #c7d7fe !important;
    border-radius: 14px !important;
}
[data-testid="stDataFrame"] { overflow-x: auto; }
.block-container { padding-top: 1.55rem; padding-bottom: 2.6rem; max-width: 1180px; }

@media (max-width: 768px) {
    html { font-size: 16px; }
    .block-container { padding: 1rem 0.8rem 2.2rem !important; max-width: 100%; }
    .hero { padding: 1.15rem 1.05rem; border-radius: 16px; }
    .hero h1 { font-size: 1.55rem; }
    .score-hero { padding: 1rem; }
    .ring { width: 92px; height: 92px; }
    .ring-inner { width: 70px; height: 70px; }
    .ring-inner strong { font-size: 1.28rem; }
    [data-testid="stHorizontalBlock"] { flex-wrap: wrap !important; }
    [data-testid="stHorizontalBlock"] > div {
        width: 100% !important; min-width: 100% !important; flex: 1 1 100% !important;
    }
    .stButton > button { width: 100%; min-height: 52px; }
    .stTextArea textarea { min-height: 170px !important; }
}
.back-row { margin: 0 0 0.7rem; }
@media (min-width: 769px) {
    .hero h1 { font-size: 2.25rem; }
    .back-row .stButton > button { width: auto; min-width: 168px; min-height: 42px !important; }
}
</style>
"""


def _hero(kicker: str, title: str, subtitle: str, steps: list[str]) -> None:
    pills = "".join(f'<span class="step"><b>{i}</b>{html.escape(step)}</span>' for i, step in enumerate(steps, 1))
    st.markdown(
        f"""
        <div class="hero">
            <div class="kicker">{html.escape(kicker)}</div>
            <h1>{html.escape(title)}</h1>
            <p>{html.escape(subtitle)}</p>
            <div class="hero-steps">{pills}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _card_head(icon: str, title: str, hint: str, tone: str) -> None:
    st.markdown(
        f"""
        <div class="card-head">
            <div class="card-ico ico-{tone}">{html.escape(icon)}</div>
            <div><h3>{html.escape(title)}</h3><span>{html.escape(hint)}</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _empty(title: str, body: str) -> None:
    st.markdown(
        f'<div class="empty"><div class="mark">FR</div><strong>{html.escape(title)}</strong>{html.escape(body)}</div>',
        unsafe_allow_html=True,
    )


def _chips(items: list[str], kind: str) -> str:
    cls = {"ok": "chip-ok", "miss": "chip-miss", "pref": "chip-pref", "extra": "chip-extra"}[kind]
    if not items:
        return "<span class='muted'>None found</span>"
    return " ".join(f'<span class="chip {cls}">{html.escape(item)}</span>' for item in items)


def _verdict_class(verdict: str) -> str:
    return {
        "Strong fit": "v-strong",
        "Good fit": "v-good",
        "Partial fit": "v-partial",
        "Weak fit": "v-weak",
    }.get(verdict, "v-good")


def _score_panel(score: float, verdict: str) -> None:
    width = max(0.0, min(score, 100.0))
    st.markdown(
        f"""
        <div class="score-hero">
            <div class="ring" style="background:conic-gradient(#2563eb {width}%, #e8edf5 0)">
                <div class="ring-inner"><strong>{score:.0f}</strong><small>/ 100</small></div>
            </div>
            <div class="score-copy">
                <div class="label">Match score</div>
                <div class="score-verdict {_verdict_class(verdict)}">{html.escape(verdict)}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _skill_block(title: str, items: list[str], kind: str) -> None:
    st.markdown(f'<div class="panel-label">{html.escape(title)}</div>', unsafe_allow_html=True)
    st.markdown(_chips(items, kind), unsafe_allow_html=True)


def _ingest(label: str, key: str, height: int = 280, placeholder: str = "") -> str:
    uploaded = st.file_uploader(f"Upload {label}", type=["txt", "pdf", "docx"], key=f"{key}_file")
    if uploaded is not None and uploaded.name != st.session_state.get(f"_{key}_file_name"):
        st.session_state[f"{key}_area"] = load_uploaded_file(uploaded.name, uploaded.getvalue())
        st.session_state[f"_{key}_file_name"] = uploaded.name
    return st.text_area(
        f"{label.capitalize()} text",
        height=height,
        key=f"{key}_area",
        placeholder=placeholder,
    )


def page_screen() -> None:
    _hero(
        "Screen",
        "See the fit in seconds",
        "Upload or paste a resume and job description. FitRank extracts skills and explains the match.",
        ["Add a resume", "Add the job", "Get a scored report"],
    )
    left, right = st.columns(2, gap="large")
    with left:
        with st.container(border=True):
            _card_head("CV", "Resume", "PDF, DOCX, or pasted text", "blue")
            resume_text = _ingest("resume", "resume", placeholder="Paste the candidate resume here.")
    with right:
        with st.container(border=True):
            _card_head("JD", "Job description", "Requirements and preferred skills", "teal")
            jd_text = _ingest("job description", "jd", placeholder="Paste the role requirements here.")

    st.write("")
    if st.button("Compute match score", type="primary", use_container_width=True):
        if not resume_text.strip() or not jd_text.strip():
            st.error("Add both a resume and a job description to continue.")
        else:
            with st.spinner("Analyzing resume and job description…"):
                st.session_state["screen_result"] = screen(resume_text, jd_text)

    out = st.session_state.get("screen_result")
    if not out:
        _empty("Ready when you are", "Add a resume and a job description, then compute the match score.")
        return

    gap = out["gap_report"]
    years = gap["experience"]["resume_years"]
    top, side = st.columns([1.15, 1.85], gap="large")
    with top:
        _score_panel(out["score"], gap["verdict"])
    with side:
        a, b, c = st.columns(3)
        a.metric("Required coverage", f"{gap['required_coverage_pct']}%")
        b.metric("Experience", "Not stated" if years is None else f"{years:g} yrs")
        c.metric("Education", out["resume"]["education"]["degree"] or "Not stated")

    with st.container(border=True):
        st.markdown('<div class="panel-label">Score breakdown</div>', unsafe_allow_html=True)
        st.dataframe(
            [{"Component": name, "Score": value} for name, value in out["breakdown"].items()],
            use_container_width=True,
            hide_index=True,
        )

    g1, g2 = st.columns(2, gap="large")
    with g1:
        with st.container(border=True):
            _skill_block("Matched required skills", gap["matched_required"], "ok")
            st.write("")
            _skill_block("Additional resume skills", gap["extra_skills"][:16], "extra")
    with g2:
        with st.container(border=True):
            _skill_block("Missing required skills", gap["missing_required"], "miss")
            st.write("")
            _skill_block("Missing preferred skills", gap["missing_preferred"], "pref")

    with st.container(border=True):
        st.markdown('<div class="panel-label">Recommendations</div>', unsafe_allow_html=True)
        for tip in gap["suggestions"]:
            st.markdown(f'<div class="tip">{html.escape(tip)}</div>', unsafe_allow_html=True)


def _current_page() -> str:
    page = st.session_state.get("nav_page", "Screen")
    if page not in PAGES:
        page = "Screen"
        st.session_state["nav_page"] = page
    return page


def _go_to(page: str) -> None:
    st.session_state["nav_page"] = page
    st.rerun()


def _nav_buttons(prefix: str) -> None:
    current = _current_page()
    left, right = st.columns(2)
    with left:
        if st.button(
            "Screen",
            key=f"{prefix}_screen",
            type="primary" if current == "Screen" else "secondary",
            use_container_width=True,
        ) and current != "Screen":
            _go_to("Screen")
    with right:
        if st.button(
            "Resume builder",
            key=f"{prefix}_builder",
            type="primary" if current == "Resume builder" else "secondary",
            use_container_width=True,
        ) and current != "Resume builder":
            _go_to("Resume builder")


def _photo_from_upload(uploaded) -> tuple[bytes | None, str]:
    if uploaded is None:
        return None, "image/jpeg"
    name = (uploaded.name or "").lower()
    mime = "image/png" if name.endswith(".png") else "image/jpeg"
    return uploaded.getvalue(), mime


def _sync_editor(doc: dict) -> None:
    for key, value in {
        "edit_name": doc.get("name", ""),
        "edit_title": doc.get("title", ""),
        "edit_email": doc.get("email", ""),
        "edit_phone": doc.get("phone", ""),
        "edit_location": doc.get("location", ""),
        "edit_summary": doc.get("summary", ""),
        "edit_skills": doc.get("skills", ""),
        "edit_experience": doc.get("experience", ""),
        "edit_education": doc.get("education", ""),
        "edit_projects": doc.get("projects", ""),
        "edit_certs": doc.get("certifications", ""),
    }.items():
        st.session_state[key] = value


def _editor_doc() -> dict:
    return {
        "name": st.session_state.get("edit_name", ""),
        "title": st.session_state.get("edit_title", ""),
        "email": st.session_state.get("edit_email", ""),
        "phone": st.session_state.get("edit_phone", ""),
        "location": st.session_state.get("edit_location", ""),
        "summary": st.session_state.get("edit_summary", ""),
        "skills": st.session_state.get("edit_skills", ""),
        "experience": st.session_state.get("edit_experience", ""),
        "education": st.session_state.get("edit_education", ""),
        "projects": st.session_state.get("edit_projects", ""),
        "certifications": st.session_state.get("edit_certs", ""),
    }


def page_builder() -> None:
    st.markdown('<div class="back-row">', unsafe_allow_html=True)
    if st.button("← Back to Screen", key="builder_back"):
        _go_to("Screen")
    st.markdown("</div>", unsafe_allow_html=True)
    _hero(
        "Builder",
        "Draft a resume for the role",
        "Pick a layout, paste the job, then preview, edit, and download a PDF.",
        ["Choose a format", "Build from the JD", "Edit preview and download PDF"],
    )

    with st.container(border=True):
        _card_head("FM", "Resume format", "Match the sample layouts: photo sidebar or clean two-column.", "blue")
        st.markdown(
            """
            <div class="format-grid">
              <div class="format-card"><strong>With photo</strong>
                <div class="mock mock-photo"><div class="s"></div><div class="m"><div class="bar short"></div><div class="bar"></div><div class="bar"></div></div></div>
              </div>
              <div class="format-card"><strong>Without photo</strong>
                <div class="mock mock-plain"><div class="bar short"></div><div class="bar"></div><div class="bar"></div></div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        format_label = st.radio(
            "Layout",
            ["With photo", "Without photo"],
            horizontal=True,
            key="resume_format_label",
        )
        layout = PHOTO if format_label == "With photo" else NO_PHOTO
        photo = st.file_uploader("Profile photo", type=["png", "jpg", "jpeg"], key="resume_photo") if layout == PHOTO else None
        photo_bytes, photo_mime = _photo_from_upload(photo)
        if photo_bytes:
            st.session_state["resume_photo_bytes"] = photo_bytes
            st.session_state["resume_photo_mime"] = photo_mime
        elif layout != PHOTO:
            st.session_state.pop("resume_photo_bytes", None)

    with st.container(border=True):
        _card_head("JD", "Job description", "The role you want the resume to target", "teal")
        jd_text = _ingest("job description", "build_jd", height=220, placeholder="Paste the job you are targeting.")

    c1, c2, c3 = st.columns(3)
    with c1:
        name = st.text_input("Your name", placeholder="Full name")
    with c2:
        contact = st.text_input("Contact", placeholder="email | phone | city")
    with c3:
        title = st.text_input("Target title", placeholder="e.g. Backend Engineer")

    with st.container(border=True):
        _card_head("CV", "Your current resume", "Optional. Used so the draft stays truthful.", "blue")
        source = _ingest(
            "current resume",
            "build_resume",
            height=200,
            placeholder="Paste your existing resume so the draft uses your real experience.",
        )

    if st.button("Build tailored resume", type="primary", use_container_width=True):
        if not jd_text.strip():
            st.error("Add a job description first.")
        else:
            with st.spinner("Building a JD-aligned draft…"):
                built = build_resume(
                    jd_text,
                    source_resume=source,
                    name=name,
                    contact=contact,
                    target_title=title,
                )
                st.session_state["builder_result"] = built
                _sync_editor(ensure_doc(built))

    out = st.session_state.get("builder_result")
    if not out:
        _empty(
            "No draft yet",
            "Choose a format, add a job description, then build. You can edit the preview and download a PDF.",
        )
        return
    if "edit_name" not in st.session_state:
        _sync_editor(ensure_doc(out))

    m1, m2, m3 = st.columns(3)
    m1.metric("Target role", out["role"][:28] + ("…" if len(out["role"]) > 28 else ""))
    m2.metric("JD skills used", str(len(out["required_skills"])))
    m3.metric("Used your resume", "Yes" if out["used_source_resume"] else "Template")

    g1, g2 = st.columns(2, gap="large")
    with g1:
        with st.container(border=True):
            _skill_block("Skills to lead with", out["matched_skills"] or out["required_skills"][:8], "ok")
    with g2:
        with st.container(border=True):
            _skill_block("Add only if true for you", out["missing_required"], "miss")

    edit_tab, preview_tab = st.tabs(["Edit", "Preview"])
    with edit_tab:
        with st.container(border=True):
            a, b = st.columns(2)
            with a:
                st.text_input("Name", key="edit_name")
                st.text_input("Title", key="edit_title")
                st.text_input("Email", key="edit_email")
            with b:
                st.text_input("Phone", key="edit_phone")
                st.text_input("Location", key="edit_location")
                st.text_input("Skills", key="edit_skills")
            st.text_area("Professional summary", height=110, key="edit_summary")
            st.text_area("Experience", height=180, key="edit_experience")
            st.text_area("Education", height=110, key="edit_education")
            st.text_area("Projects", height=110, key="edit_projects")
            st.text_area("Certifications", height=90, key="edit_certs")

    doc = _editor_doc()
    stored_photo = st.session_state.get("resume_photo_bytes") if layout == PHOTO else None
    stored_mime = st.session_state.get("resume_photo_mime", "image/jpeg")
    preview_html = render_html(doc, layout, stored_photo, stored_mime)
    pdf_bytes = render_pdf(doc, layout, stored_photo)

    with preview_tab:
        st.download_button(
            "Download PDF",
            data=pdf_bytes,
            file_name="tailored_resume.pdf",
            mime="application/pdf",
            use_container_width=True,
            key="download_resume_pdf",
        )
        st.markdown('<div class="preview-wrap">', unsafe_allow_html=True)
        st.components.v1.html(preview_html, height=1080, scrolling=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.download_button(
        "Download PDF",
        data=pdf_bytes,
        file_name="tailored_resume.pdf",
        mime="application/pdf",
        use_container_width=True,
        key="download_resume_pdf_main",
    )


def main() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
    if "nav_page" not in st.session_state or st.session_state["nav_page"] not in PAGES:
        st.session_state["nav_page"] = "Screen"
    with st.sidebar:
        st.markdown(
            """<div class="brand">
                <div class="brand-mark">FR</div>
                <div><h2>FitRank</h2><p>Screen · Build</p></div>
            </div>""",
            unsafe_allow_html=True,
        )
        _nav_buttons("side")
        st.markdown(
            '<div class="side-note">Screen a resume against a job, or draft a resume aimed at that job.</div>',
            unsafe_allow_html=True,
        )
    st.markdown('<div class="nav-bar">', unsafe_allow_html=True)
    _nav_buttons("top")
    st.markdown("</div>", unsafe_allow_html=True)
    {"Screen": page_screen, "Resume builder": page_builder}[_current_page()]()


if __name__ == "__main__":
    main()
