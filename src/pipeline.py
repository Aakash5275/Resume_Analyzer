"""Screening, ranking, and evaluation entry points."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

from .evaluate import evaluate_ranking
from .gap import build_gap_report
from .kaggle_data import CACHE_PATH, load_or_build_dataset
from .match import MatchResult, match_resume_to_jd

DATA_PATH = CACHE_PATH


def load_dataset(path: Optional[Path] = None, force_refresh: bool = False) -> Dict:
    if path is not None:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    return load_or_build_dataset(force=force_refresh)


def screen(resume_text: str, jd_text: str, weights: Optional[Dict[str, float]] = None) -> Dict:
    result: MatchResult = match_resume_to_jd(resume_text, jd_text, weights=weights)
    return {
        "score": result.overall_score,
        "breakdown": result.breakdown.as_percent(),
        "weights": result.weights,
        "resume": {
            "skills": result.resume_profile.skills,
            "years": result.resume_profile.experience.years,
            "titles": result.resume_profile.experience.titles,
            "education": {
                "degree": result.resume_profile.education.degree,
                "field": result.resume_profile.education.field_of_study,
                "institution": result.resume_profile.education.institution,
            },
        },
        "jd": {
            "skills": result.jd_profile.skills,
            "required_skills": result.jd_profile.required_skills,
            "preferred_skills": result.jd_profile.preferred_skills,
            "years": result.jd_profile.experience.years,
            "education": result.jd_profile.education.degree,
        },
        "gap_report": build_gap_report(result),
    }


def run_full_evaluation(dataset: Optional[Dict] = None) -> Dict:
    dataset = dataset or load_dataset()
    resumes = [{"id": r["id"], "name": r["name"], "text": r["text"]} for r in dataset["resumes"]]
    jds = {j["id"]: j for j in dataset["job_descriptions"]}
    eval_ids = set((dataset.get("source") or {}).get("eval_jd_ids") or jds)
    reports = []
    for jd_id, relevance in dataset["rankings"].items():
        if jd_id not in eval_ids:
            continue
        gold = {row["resume_id"]: float(row["relevance"]) for row in relevance}
        report = evaluate_ranking(resumes, jds[jd_id]["text"], gold, k=5)
        reports.append(
            {
                "jd_id": jd_id,
                "title": jds[jd_id]["title"],
                "ndcg@5": report["ndcg"],
                "spearman": report["correlation"]["spearman"],
                "kendall": report["correlation"]["kendall"],
                "predicted_order": report["predicted_order"],
                "scores": report["scores"],
            }
        )
    return {"ranking": reports}


def dataset_resumes() -> List[Dict]:
    return load_dataset()["resumes"]


def dataset_jds() -> List[Dict]:
    return load_dataset()["job_descriptions"]
