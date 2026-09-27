"""Text preprocessing for resumes and job descriptions.

Pipeline: lowercase → noise stripping → tokenization → stopword removal →
lemmatization. A small built-in stopword list is used so the project still
runs if NLTK data has not been downloaded; WordNet lemmatization is used
when available.
"""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from typing import List

_NLTK_READY = False

BUILTIN_STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "then", "else", "when", "at",
    "by", "for", "with", "about", "against", "between", "into", "through",
    "during", "before", "after", "above", "below", "to", "from", "up", "down",
    "in", "out", "on", "off", "over", "under", "again", "further", "once",
    "here", "there", "all", "any", "both", "each", "few", "more", "most",
    "other", "some", "such", "no", "nor", "not", "only", "own", "same", "so",
    "than", "too", "very", "can", "will", "just", "should", "now", "of", "is",
    "are", "was", "were", "be", "been", "being", "have", "has", "had", "do",
    "does", "did", "this", "that", "these", "those", "i", "you", "he", "she",
    "it", "we", "they", "me", "him", "her", "us", "them", "my", "your", "his",
    "its", "our", "their", "what", "which", "who", "whom", "as", "until",
    "while", "because", "although", "also", "using", "used", "use", "etc",
    "including", "include", "across", "within", "per", "via", "able",
}

EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
PHONE_RE = re.compile(r"\+?\d[\d\s().-]{7,}\d")
WHITESPACE_RE = re.compile(r"\s+")
NON_ALNUM_RE = re.compile(r"[^a-z0-9+#.\-\s]")


def ensure_nltk() -> bool:
    """Download lightweight NLTK resources on first use. Returns True if ready."""
    global _NLTK_READY
    if _NLTK_READY:
        return True
    try:
        import nltk

        resources = {
            "tokenizers/punkt": "punkt",
            "tokenizers/punkt_tab": "punkt_tab",
            "corpora/stopwords": "stopwords",
            "corpora/wordnet": "wordnet",
            "corpora/omw-1.4": "omw-1.4",
            "taggers/averaged_perceptron_tagger": "averaged_perceptron_tagger",
            "taggers/averaged_perceptron_tagger_eng": "averaged_perceptron_tagger_eng",
        }
        for path, name in resources.items():
            try:
                nltk.data.find(path)
            except LookupError:
                nltk.download(name, quiet=True)
        _NLTK_READY = True
        return True
    except Exception:
        return False


@lru_cache(maxsize=1)
def _stopwords() -> set[str]:
    words = set(BUILTIN_STOPWORDS)
    if ensure_nltk():
        try:
            from nltk.corpus import stopwords

            words |= set(stopwords.words("english"))
        except Exception:
            pass
    return words


def normalize_unicode(text: str) -> str:
    return unicodedata.normalize("NFKC", text or "")


def clean_text(text: str, strip_contacts: bool = True) -> str:
    """Lowercase, strip URLs/emails/phones, keep skill-relevant symbols like + # ."""
    text = normalize_unicode(text)
    text = text.replace("\x00", " ")
    if strip_contacts:
        text = EMAIL_RE.sub(" ", text)
        text = URL_RE.sub(" ", text)
        text = PHONE_RE.sub(" ", text)
    text = text.lower()
    text = text.replace("/", " ").replace("\\", " ")
    text = NON_ALNUM_RE.sub(" ", text)
    text = WHITESPACE_RE.sub(" ", text).strip()
    return text


def tokenize(text: str) -> List[str]:
    if ensure_nltk():
        try:
            from nltk.tokenize import word_tokenize

            return [t for t in word_tokenize(text) if t.strip()]
        except Exception:
            pass
    return [t for t in re.findall(r"[a-z0-9+#]+(?:[.-][a-z0-9+#]+)*", text) if t]


def lemmatize_tokens(tokens: List[str]) -> List[str]:
    if ensure_nltk():
        try:
            from nltk.stem import WordNetLemmatizer

            lemma = WordNetLemmatizer()
            return [lemma.lemmatize(tok) for tok in tokens]
        except Exception:
            pass
    return tokens


def preprocess(text: str, remove_stopwords: bool = True, lemmatize: bool = True) -> str:
    """Return a cleaned, tokenized, optionally stopword-filtered lemma string."""
    cleaned = clean_text(text)
    tokens = tokenize(cleaned)
    if remove_stopwords:
        stops = _stopwords()
        tokens = [t for t in tokens if t not in stops and len(t) > 1]
    if lemmatize:
        tokens = lemmatize_tokens(tokens)
    return " ".join(tokens)


def sentences(text: str) -> List[str]:
    raw = normalize_unicode(text or "")
    if ensure_nltk():
        try:
            from nltk.tokenize import sent_tokenize

            return [s.strip() for s in sent_tokenize(raw) if s.strip()]
        except Exception:
            pass
    parts = re.split(r"(?<=[.!?])\s+|\n+", raw)
    return [p.strip() for p in parts if p.strip()]
