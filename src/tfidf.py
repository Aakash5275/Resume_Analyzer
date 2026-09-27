"""TF-IDF cosine similarity implemented with NumPy (no scikit-learn)."""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import List, Sequence

import numpy as np

from .preprocess import preprocess

TOKEN_RE = re.compile(r"[a-z0-9+#]+(?:[.-][a-z0-9+#]+)*")


def _ngrams(tokens: Sequence[str], ngram_range=(1, 2)) -> List[str]:
    lo, hi = ngram_range
    grams: List[str] = []
    n = len(tokens)
    for size in range(lo, hi + 1):
        for i in range(n - size + 1):
            grams.append(" ".join(tokens[i : i + size]))
    return grams


def _tokenize_doc(text: str) -> List[str]:
    processed = preprocess(text, lemmatize=False)
    tokens = TOKEN_RE.findall(processed)
    return _ngrams(tokens, (1, 2))


def tfidf_cosine(
    resume_text: str,
    jd_text: str,
    extra_a: Sequence[str] | None = None,
    extra_b: Sequence[str] | None = None,
) -> float:
    """Cosine similarity of two documents in a 2-document TF-IDF space."""
    left = f"{resume_text} {' '.join(extra_a or [])}"
    right = f"{jd_text} {' '.join(extra_b or [])}"
    docs = [_tokenize_doc(left), _tokenize_doc(right)]
    if not docs[0] or not docs[1]:
        return 0.0

    vocab = sorted(set(docs[0]) | set(docs[1]))
    index = {term: i for i, term in enumerate(vocab)}
    n_docs = 2
    df = Counter()
    for doc in docs:
        df.update(set(doc))

    idf = np.array(
        [math.log((1 + n_docs) / (1 + df[term])) + 1.0 for term in vocab],
        dtype=float,
    )

    vectors = []
    for doc in docs:
        tf = Counter(doc)
        vec = np.zeros(len(vocab), dtype=float)
        for term, count in tf.items():
            vec[index[term]] = (1.0 + math.log(count)) * idf[index[term]]
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm
        vectors.append(vec)

    sim = float(np.dot(vectors[0], vectors[1]))
    return float(np.clip(sim, 0.0, 1.0))
