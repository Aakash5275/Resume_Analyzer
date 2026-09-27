"""Print ranking metrics for the Kaggle working set."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pipeline import run_full_evaluation


def main() -> None:
    report = run_full_evaluation()
    print("Resume Screener - ranking on Kaggle snehaanbhawal/resume-dataset")
    for row in report["ranking"]:
        print(
            f"  {row['title']:<28}  nDCG@5={row['ndcg@5']:.3f}  "
            f"Spearman={row['spearman']:.3f}  Kendall={row['kendall']:.3f}"
        )
        print(f"    top: {' > '.join(row['predicted_order'][:5])}")
    out = ROOT / "data" / "evaluation" / "last_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
