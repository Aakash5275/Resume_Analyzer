"""Score a resume or rank cached Kaggle resumes against a JD."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.io_utils import SUPPORTED_SUFFIXES, load_document
from src.match import rank_resumes
from src.pipeline import load_dataset, screen


def _collect_resumes(folder: Path):
    items = []
    for path in sorted(folder.iterdir()):
        if path.suffix.lower() in SUPPORTED_SUFFIXES:
            items.append({"id": path.stem, "name": path.stem, "text": load_document(path)})
    return items


def main() -> None:
    parser = argparse.ArgumentParser(description="Resume Screener")
    parser.add_argument("--resume", help="Resume file (txt/pdf/docx)")
    parser.add_argument("--jd", help="Job description file")
    parser.add_argument("--resume-id", help="Kaggle resume id from the working set")
    parser.add_argument("--jd-id", help="Cached JD id, for example jd_information-technology")
    parser.add_argument("--resumes-dir", help="Folder of resumes to rank")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    dataset = None
    if args.resume_id or args.jd_id:
        dataset = load_dataset()

    if args.jd_id:
        jd = next((j for j in dataset["job_descriptions"] if j["id"] == args.jd_id), None)
        if not jd:
            parser.error(f"Unknown --jd-id {args.jd_id}")
        jd_text = jd["text"]
    elif args.jd:
        jd_text = load_document(args.jd)
    else:
        parser.error("Provide --jd or --jd-id")

    if args.resumes_dir:
        ranked = rank_resumes(_collect_resumes(Path(args.resumes_dir)), jd_text)
        payload = [
            {"rank": r["rank"], "id": r["id"], "name": r["name"], "score": r["score"]}
            for r in ranked
        ]
        print(json.dumps(payload, indent=2) if args.json else "\n".join(
            f"{row['rank']:>2}. {row['name']:<32} {row['score']:5.1f}" for row in payload
        ))
        return

    if args.resume_id:
        resume = next((r for r in dataset["resumes"] if r["id"] == args.resume_id), None)
        if not resume:
            parser.error(f"Unknown --resume-id {args.resume_id}")
        resume_text = resume["text"]
    elif args.resume:
        resume_text = load_document(args.resume)
    else:
        parser.error("Provide --resume, --resume-id, or --resumes-dir")

    result = screen(resume_text, jd_text)
    if args.json:
        print(json.dumps({k: v for k, v in result.items() if k != "result"}, indent=2, default=str))
        return
    gap = result["gap_report"]
    print(f"Match score: {result['score']:.1f}  ({gap['verdict']})")
    print(f"Required coverage: {gap['required_coverage_pct']}%")
    print(f"Matched: {', '.join(gap['matched_required']) or '-'}")
    print(f"Missing: {', '.join(gap['missing_required']) or '-'}")


if __name__ == "__main__":
    main()
