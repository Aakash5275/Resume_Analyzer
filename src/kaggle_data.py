"""Load the public Kaggle resume corpus (snehaanbhawal/resume-dataset).

The Kaggle set has real resume text and a job Category label. It does not
include job descriptions or skill spans, so JDs are built from frequent
skills observed in each category, and ranking gold uses Category match.
"""

from __future__ import annotations

import csv
import json
import re
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Set

ROOT = Path(__file__).resolve().parent.parent
CACHE_PATH = ROOT / "data" / "kaggle_cache" / "processed.json"
KAGGLE_SLUG = "snehaanbhawal/resume-dataset"
CSV_CANDIDATES = ("Resume/Resume.csv", "Resume.csv", "resume.csv")

# Read enough resumes per category to estimate JD skills; keep a smaller
# working set so the UI and ranking stay usable.
SKILL_SAMPLE_PER_CATEGORY = 15
WORKING_SET_PER_CATEGORY = 3
MAX_RESUME_CHARS = 12000

RELATED_CATEGORIES = {
    "INFORMATION-TECHNOLOGY": {"ENGINEERING", "DIGITAL-MEDIA", "CONSULTANT"},
    "ENGINEERING": {"INFORMATION-TECHNOLOGY", "CONSTRUCTION", "AUTOMOBILE", "AVIATION"},
    "DIGITAL-MEDIA": {"INFORMATION-TECHNOLOGY", "DESIGNER", "PUBLIC-RELATIONS", "ARTS"},
    "DESIGNER": {"DIGITAL-MEDIA", "ARTS", "APPAREL"},
    "ARTS": {"DESIGNER", "DIGITAL-MEDIA", "APPAREL"},
    "APPAREL": {"DESIGNER", "ARTS", "SALES"},
    "FINANCE": {"ACCOUNTANT", "BANKING"},
    "ACCOUNTANT": {"FINANCE", "BANKING"},
    "BANKING": {"FINANCE", "ACCOUNTANT"},
    "SALES": {"BUSINESS-DEVELOPMENT", "PUBLIC-RELATIONS", "BPO"},
    "BUSINESS-DEVELOPMENT": {"SALES", "CONSULTANT", "PUBLIC-RELATIONS"},
    "PUBLIC-RELATIONS": {"SALES", "BUSINESS-DEVELOPMENT", "DIGITAL-MEDIA"},
    "HR": {"CONSULTANT", "BPO", "BUSINESS-DEVELOPMENT"},
    "CONSULTANT": {"HR", "BUSINESS-DEVELOPMENT", "INFORMATION-TECHNOLOGY"},
    "BPO": {"HR", "SALES", "PUBLIC-RELATIONS"},
    "HEALTHCARE": {"FITNESS"},
    "FITNESS": {"HEALTHCARE"},
    "TEACHER": {"CONSULTANT"},
    "ADVOCATE": {"CONSULTANT", "HR"},
    "CONSTRUCTION": {"ENGINEERING"},
    "AUTOMOBILE": {"ENGINEERING", "AVIATION"},
    "AVIATION": {"ENGINEERING", "AUTOMOBILE"},
    "AGRICULTURE": {"CONSTRUCTION", "ENGINEERING"},
    "CHEF": {"FITNESS"},
}


def _clean_resume_text(text: str) -> str:
    text = (text or "").replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()[:MAX_RESUME_CHARS]


def _title(category: str) -> str:
    return category.replace("-", " ").replace("_", " ").title()


def _relevance(resume_cat: str, jd_cat: str) -> int:
    if resume_cat == jd_cat:
        return 3
    if resume_cat in RELATED_CATEGORIES.get(jd_cat, set()):
        return 1
    return 0


def _find_csv(root: Path) -> Path:
    matches = list(root.rglob("Resume.csv")) + list(root.rglob("resume.csv"))
    if not matches:
        raise FileNotFoundError(f"Resume.csv not found under {root}")
    return matches[0]


def _rows_from_pandas(df) -> List[Dict[str, str]]:
    columns = {str(c).strip(): c for c in df.columns}
    id_col = columns.get("ID") or columns.get("id")
    text_col = columns.get("Resume_str") or columns.get("Resume") or columns.get("resume")
    cat_col = columns.get("Category") or columns.get("category")
    if text_col is None or cat_col is None:
        raise ValueError(f"Unexpected columns: {list(df.columns)}")
    rows = []
    for rec in df.to_dict(orient="records"):
        rows.append(
            {
                "id": str(rec.get(id_col, "")).strip(),
                "text": _clean_resume_text(str(rec.get(text_col) or "")),
                "category": str(rec.get(cat_col) or "").strip().upper().replace(" ", "-"),
            }
        )
    return rows


def _rows_from_csv(path: Path) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    with path.open("r", encoding="utf-8", errors="ignore", newline="") as handle:
        reader = csv.DictReader(handle)
        for rec in reader:
            lower = {k.lower().strip(): v for k, v in rec.items() if k}
            text = lower.get("resume_str") or lower.get("resume") or ""
            category = (lower.get("category") or "").strip().upper().replace(" ", "-")
            rid = (lower.get("id") or "").strip()
            if not text.strip() or not category:
                continue
            rows.append({"id": rid, "text": _clean_resume_text(text), "category": category})
    return rows


def download_kaggle_rows() -> List[Dict[str, str]]:
    """Download snehaanbhawal/resume-dataset via kagglehub (pandas adapter, CSV fallback)."""
    import kagglehub

    last_error: Optional[Exception] = None
    try:
        from kagglehub import KaggleDatasetAdapter

        load_fn = getattr(kagglehub, "dataset_load", None) or kagglehub.load_dataset
        for file_path in CSV_CANDIDATES:
            try:
                df = load_fn(
                    KaggleDatasetAdapter.PANDAS,
                    KAGGLE_SLUG,
                    file_path,
                )
                print(f"Loaded Kaggle file {file_path!r} via pandas adapter: {len(df)} rows")
                print("First 5 records:")
                print(df.head())
                return [row for row in _rows_from_pandas(df) if row["text"] and row["category"]]
            except Exception as exc:  # pandas policy, missing path, etc.
                last_error = exc
                continue
    except Exception as exc:
        last_error = exc

    csv_path = None
    for file_path in CSV_CANDIDATES:
        try:
            downloaded = Path(kagglehub.dataset_download(KAGGLE_SLUG, path=file_path))
            if downloaded.is_file():
                csv_path = downloaded
                break
            found = _find_csv(downloaded)
            csv_path = found
            break
        except Exception:
            continue
    if csv_path is None:
        local_dir = Path(kagglehub.dataset_download(KAGGLE_SLUG))
        csv_path = _find_csv(local_dir)
    print(f"Loaded Kaggle CSV from {csv_path} (fallback reader)")
    if last_error:
        print(f"pandas adapter note: {last_error}")
    return _rows_from_csv(csv_path)


def _pick_evenly(items: List[Dict], n: int) -> List[Dict]:
    items = [x for x in items if x["text"]]
    items.sort(key=lambda x: x["id"])
    return items[:n]


def _build_jd_text(category: str, required: List[str], preferred: List[str]) -> str:
    title = _title(category)
    req_lines = "\n".join(f"- {skill}" for skill in required) or "- Relevant professional experience"
    pref_lines = "\n".join(f"- {skill}" for skill in preferred) or "- Communication"
    return (
        f"{title} — Open Role\n"
        f"We are hiring a {title} professional with 3+ years of experience.\n\n"
        f"Responsibilities\n"
        f"- Deliver work typical of the {title} function using the skills below.\n"
        f"- Collaborate across teams and document outcomes.\n\n"
        f"Requirements\n"
        f"{req_lines}\n"
        f"- Bachelor's degree or equivalent experience.\n\n"
        f"Preferred\n"
        f"{pref_lines}\n"
        f"- Leadership and problem solving.\n"
    )


def _distinctive_skills(cat_docs: Dict[str, List[Set[str]]]) -> Dict[str, List[str]]:
    """Rank skills by in-category rate times inverse category frequency."""
    n_cats = max(len(cat_docs), 1)
    category_df: Counter[str] = Counter()
    for docs in cat_docs.values():
        present: Set[str] = set()
        for doc in docs:
            present.update(doc)
        for skill in present:
            category_df[skill] += 1

    ranked: Dict[str, List[str]] = {}
    for category, docs in cat_docs.items():
        n = max(len(docs), 1)
        tf: Counter[str] = Counter()
        for doc in docs:
            tf.update(doc)
        scored = []
        for skill, count in tf.items():
            idf = math.log((1.0 + n_cats) / (1.0 + category_df[skill])) + 1.0
            scored.append((skill, (count / n) * idf))
        scored.sort(key=lambda item: item[1], reverse=True)
        ranked[category] = [name for name, _ in scored]
    return ranked


def build_processed_dataset(rows: List[Dict[str, str]]) -> Dict:
    from .extract import extract_skills

    by_cat: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for row in rows:
        if row["id"] and row["text"] and row["category"]:
            by_cat[row["category"]].append(row)

    categories = sorted(by_cat)
    resumes: List[Dict] = []
    jds: List[Dict] = []
    rankings: Dict[str, List[Dict]] = {}

    cat_skill_docs: Dict[str, List[Set[str]]] = {}
    for category in categories:
        skill_docs = _pick_evenly(by_cat[category], SKILL_SAMPLE_PER_CATEGORY)
        cat_skill_docs[category] = [
            set(extract_skills(doc["text"], fuzzy_threshold=0)[0]) for doc in skill_docs
        ]
    distinctive = _distinctive_skills(cat_skill_docs)

    for category in categories:
        top = distinctive.get(category, [])
        required = top[:8]
        preferred = top[8:14]
        jd_id = f"jd_{category.lower()}"
        jds.append(
            {
                "id": jd_id,
                "title": _title(category),
                "category": category,
                "text": _build_jd_text(category, required, preferred),
                "gold_skills": required + preferred,
            }
        )

        for doc in _pick_evenly(by_cat[category], WORKING_SET_PER_CATEGORY):
            resumes.append(
                {
                    "id": doc["id"],
                    "name": f"{_title(category)} #{doc['id']}",
                    "role_label": category,
                    "category": category,
                    "text": doc["text"],
                }
            )

    for jd in jds:
        rankings[jd["id"]] = [
            {
                "resume_id": resume["id"],
                "relevance": _relevance(resume["category"], jd["category"]),
            }
            for resume in resumes
        ]

    return {
        "source": {
            "kaggle": KAGGLE_SLUG,
            "url": "https://www.kaggle.com/datasets/snehaanbhawal/resume-dataset",
            "raw_rows": len(rows),
            "categories": categories,
            "working_set_per_category": WORKING_SET_PER_CATEGORY,
            "eval_jd_ids": [
                "jd_information-technology",
                "jd_finance",
                "jd_hr",
                "jd_healthcare",
                "jd_sales",
                "jd_engineering",
            ],
        },
        "resumes": resumes,
        "job_descriptions": jds,
        "rankings": rankings,
    }


def load_or_build_dataset(force: bool = False) -> Dict:
    if CACHE_PATH.exists() and not force:
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    print("Downloading and preparing Kaggle resume dataset...")
    rows = download_kaggle_rows()
    if not rows:
        raise RuntimeError("Kaggle resume dataset was empty after parsing.")
    dataset = build_processed_dataset(rows)
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(dataset, indent=2), encoding="utf-8")
    print(f"Cached processed dataset at {CACHE_PATH}")
    return dataset
