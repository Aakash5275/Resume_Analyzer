"""Download snehaanbhawal/resume-dataset and build the working set."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.kaggle_data import load_or_build_dataset


def main() -> None:
    force = "--refresh" in sys.argv
    dataset = load_or_build_dataset(force=force)
    source = dataset["source"]
    print(f"Kaggle: {source['kaggle']}")
    print(f"Raw resumes: {source['raw_rows']}")
    print(f"Categories: {len(source['categories'])}")
    print(f"Working-set resumes: {len(dataset['resumes'])}")
    print(f"Job descriptions: {len(dataset['job_descriptions'])}")
    print("Categories:", ", ".join(source["categories"]))


if __name__ == "__main__":
    main()
