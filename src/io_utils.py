"""Load resumes and job descriptions from txt, pdf, and docx files."""

from __future__ import annotations

from pathlib import Path
from typing import Optional


SUPPORTED_SUFFIXES = {".txt", ".md", ".pdf", ".docx"}


def read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def read_pdf(path: Path) -> str:
    import pdfplumber

    chunks = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            extracted = page.extract_text() or ""
            chunks.append(extracted)
    return "\n".join(chunks)


def read_docx(path: Path) -> str:
    from docx import Document

    doc = Document(str(path))
    return "\n".join(p.text for p in doc.paragraphs)


def load_document(path: str | Path) -> str:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md"}:
        return read_text_file(path)
    if suffix == ".pdf":
        return read_pdf(path)
    if suffix == ".docx":
        return read_docx(path)
    raise ValueError(f"Unsupported file type: {suffix}. Use {sorted(SUPPORTED_SUFFIXES)}")


def load_uploaded_file(name: str, data: bytes) -> str:
    suffix = Path(name).suffix.lower()
    if suffix in {".txt", ".md"}:
        return data.decode("utf-8", errors="ignore")
    tmp_dir = Path(__file__).resolve().parent.parent / ".cache_uploads"
    tmp_dir.mkdir(exist_ok=True)
    tmp_path = tmp_dir / name
    tmp_path.write_bytes(data)
    try:
        return load_document(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)


def text_or_file(text: Optional[str], file_name: Optional[str], file_bytes: Optional[bytes]) -> str:
    if file_name and file_bytes:
        return load_uploaded_file(file_name, file_bytes)
    return text or ""
