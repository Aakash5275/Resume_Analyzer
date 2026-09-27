"""Evaluation: skill-extraction F1 and ranking correlation."""

from __future__ import annotations

from typing import Dict, Iterable, List, Sequence, Tuple

import numpy as np
from scipy.stats import kendalltau, spearmanr

from .extract import extract_skills
from .match import rank_resumes


def precision_recall_f1(predicted: Iterable[str], gold: Iterable[str]) -> Dict[str, float]:
    pred, truth = set(predicted), set(gold)
    if not pred and not truth:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0, "tp": 0, "fp": 0, "fn": 0}
    tp = len(pred & truth)
    fp = len(pred - truth)
    fn = len(truth - pred)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "tp": tp,
        "fp": fp,
        "fn": fn,
    }


def micro_average(rows: List[Dict[str, float]]) -> Dict[str, float]:
    tp = sum(r["tp"] for r in rows)
    fp = sum(r["fp"] for r in rows)
    fn = sum(r["fn"] for r in rows)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "support": len(rows),
    }


def evaluate_skill_extraction(items: List[Dict]) -> Dict:
    """items: [{id, text, gold_skills}]"""
    per_doc = []
    for item in items:
        pred, _ = extract_skills(item["text"])
        metrics = precision_recall_f1(pred, item.get("gold_skills") or [])
        metrics["id"] = item.get("id", "")
        metrics["predicted"] = sorted(pred)
        metrics["gold"] = sorted(item.get("gold_skills") or [])
        per_doc.append(metrics)
    overall = micro_average(per_doc)
    return {"overall": overall, "per_document": per_doc}


def dcg(relevances: Sequence[float]) -> float:
    rel = np.asarray(relevances, dtype=float)
    if rel.size == 0:
        return 0.0
    discounts = np.log2(np.arange(2, rel.size + 2))
    return float(np.sum(rel / discounts))


def ndcg_at_k(predicted_ids: Sequence[str], gold_relevance: Dict[str, float], k: int = 10) -> float:
    k = min(k, len(predicted_ids))
    gains = [gold_relevance.get(pid, 0.0) for pid in predicted_ids[:k]]
    ideal = sorted(gold_relevance.values(), reverse=True)[:k]
    ideal_dcg = dcg(ideal)
    if ideal_dcg == 0:
        return 0.0
    return round(dcg(gains) / ideal_dcg, 4)


def ranking_correlation(
    predicted_order: Sequence[str],
    gold_relevance: Dict[str, float],
) -> Dict[str, float]:
    """Spearman / Kendall between system ranks and gold relevance grades."""
    ids = list(predicted_order)
    pred_rank = {rid: i + 1 for i, rid in enumerate(ids)}
    # Higher relevance should correspond to better (lower) rank.
    x = []
    y = []
    for rid in gold_relevance:
        if rid not in pred_rank:
            continue
        x.append(gold_relevance[rid])
        y.append(-pred_rank[rid])
    if len(x) < 3:
        return {"spearman": 0.0, "kendall": 0.0, "n": len(x)}
    rho, _ = spearmanr(x, y)
    tau, _ = kendalltau(x, y)
    return {
        "spearman": round(float(rho), 4) if rho == rho else 0.0,
        "kendall": round(float(tau), 4) if tau == tau else 0.0,
        "n": len(x),
    }


def evaluate_ranking(
    resumes: List[Dict],
    jd_text: str,
    gold_relevance: Dict[str, float],
    k: int = 5,
) -> Dict:
    ranked = rank_resumes(resumes, jd_text)
    predicted_ids = [row["id"] for row in ranked]
    corr = ranking_correlation(predicted_ids, gold_relevance)
    return {
        "predicted_order": predicted_ids,
        "scores": {row["id"]: row["score"] for row in ranked},
        "ndcg": ndcg_at_k(predicted_ids, gold_relevance, k=k),
        "correlation": corr,
        "ranked": ranked,
    }
