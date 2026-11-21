from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

SUPPORTED_EXTENSIONS = {".pdf", ".md", ".markdown", ".txt"}


@dataclass(slots=True)
class DocumentChunk:
    text: str
    source_file: str
    chunk_id: int


class TokenCounter:
    """优先使用 tiktoken，离线无缓存时自动回退到中英文词元估算。"""

    def __init__(self) -> None:
        self._encoding = None
        try:
            import tiktoken

            self._encoding = tiktoken.get_encoding("cl100k_base")
        except Exception:
            self._encoding = None

    def count(self, text: str) -> int:
        if not text:
            return 0
        if self._encoding is not None:
            return len(self._encoding.encode(text, disallowed_special=()))
        # Fallback: CJK characters ~1 token each, ASCII words/punctuation ~1 token each
        tokens = re.findall(r"[\u4e00-\u9fff]|[A-Za-z0-9_]+|[^\s\w]", text)
        return len(tokens)

    def tail_by_tokens(self, text: str, max_tokens: int) -> str:
        if max_tokens <= 0 or not text:
            return ""
        if self._encoding is not None:
            ids = self._encoding.encode(text, disallowed_special=())
            if len(ids) <= max_tokens:
                return text
            return self._encoding.decode(ids[-max_tokens:]).lstrip()
        parts = re.findall(r"[\u4e00-\u9fff]\s*|[A-Za-z0-9_]+\s*|[^\s\w]\s*", text)
        if len(parts) <= max_tokens:
            return text
        return "".join(parts[-max_tokens:]).lstrip()

    def split_text_by_tokens(self, text: str, chunk_size: int, overlap: int) -> list[str]:
        if not text.strip():
            return []
        if self._encoding is not None:
            ids = self._encoding.encode(text, disallowed_special=())
            if len(ids) <= chunk_size:
                return [text.strip()]
            step = max(1, chunk_size - overlap)
            pieces: list[str] = []
            for start in range(0, len(ids), step):
                sub = self._encoding.decode(ids[start : start + chunk_size]).strip()
                if sub:
                    pieces.append(sub)
                if start + chunk_size >= len(ids):
                    break
            return pieces

        parts = re.findall(r"[\u4e00-\u9fff]\s*|[A-Za-z0-9_]+\s*|[^\s\w]\s*", text)
        if len(parts) <= chunk_size:
            return [text.strip()]
        step = max(1, chunk_size - overlap)
        pieces = []
        for start in range(0, len(parts), step):
            sub = "".join(parts[start : start + chunk_size]).strip()
            if sub:
                pieces.append(sub)
            if start + chunk_size >= len(parts):
                break
        return pieces


def extract_text_from_file(file_path: Path) -> str:
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        return _extract_pdf_text(file_path)
    if suffix in {".md", ".markdown", ".txt"}:
        return file_path.read_text(encoding="utf-8", errors="ignore")
    raise ValueError(f"Unsupported file format: {file_path}")


def _extract_pdf_text(file_path: Path) -> str:
    try:
        import fitz  # PyMuPDF

        pages: list[str] = []
        with fitz.open(file_path) as doc:
            for page in doc:
                text = page.get_text("text")
                if text and text.strip():
                    pages.append(text.strip())
        return "\n\n".join(pages)
    except ImportError:
        from pypdf import PdfReader

        reader = PdfReader(str(file_path))
        pages = []
        for page in reader.pages:
            text = page.extract_text() or ""
            if text.strip():
                pages.append(text.strip())
        return "\n\n".join(pages)


def _split_long_paragraph(paragraph: str, counter: TokenCounter, chunk_size: int, overlap: int) -> list[str]:
    """当单个段落超过 chunk_size 时，优先按换行或句末标点细分，再兜底按 token 切分。"""
    sentences = [s.strip() for s in re.split(r"(?<=[。！？.!?])\s+|\n+", paragraph) if s.strip()]
    if len(sentences) <= 1:
        return counter.split_text_by_tokens(paragraph, chunk_size, overlap)

    units: list[str] = []
    for sent in sentences:
        if counter.count(sent) <= chunk_size:
            units.append(sent)
        else:
            units.extend(counter.split_text_by_tokens(sent, chunk_size, overlap))
    return units


def chunk_text_paragraph_first(
    text: str,
    chunk_size: int = 512,
    chunk_overlap: int = 50,
    counter: TokenCounter | None = None,
) -> list[str]:
    """按段落优先切分，每块不超过 chunk_size token，相邻块保留约 chunk_overlap token 重叠。"""
    if not text or not text.strip():
        return []

    counter = counter or TokenCounter()
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    raw_paragraphs = [p.strip() for p in re.split(r"\n{2,}", normalized) if p.strip()]

    units: list[str] = []
    for para in raw_paragraphs:
        if counter.count(para) <= chunk_size:
            units.append(para)
        else:
            units.extend(_split_long_paragraph(para, counter, chunk_size, overlap=chunk_overlap))

    chunks: list[str] = []
    current_parts: list[str] = []
    current_tokens = 0

    for unit in units:
        unit_tokens = counter.count(unit)
        if not current_parts:
            current_parts.append(unit)
            current_tokens = unit_tokens
            continue

        # 加上 "\n\n" 连接符的估算开销
        if current_tokens + unit_tokens + 1 <= chunk_size:
            current_parts.append(unit)
            current_tokens += unit_tokens + 1
        else:
            finished_chunk = "\n\n".join(current_parts).strip()
            if finished_chunk:
                chunks.append(finished_chunk)

            overlap_text = counter.tail_by_tokens(finished_chunk, chunk_overlap)
            if overlap_text and counter.count(overlap_text) + unit_tokens + 1 <= chunk_size:
                current_parts = [overlap_text, unit]
                current_tokens = counter.count(overlap_text) + unit_tokens + 1
            else:
                current_parts = [unit]
                current_tokens = unit_tokens

    if current_parts:
        last_chunk = "\n\n".join(current_parts).strip()
        if last_chunk:
            chunks.append(last_chunk)

    return chunks


def iter_source_files(source_dir: Path) -> Iterable[Path]:
    if not source_dir.exists():
        return []
    files = [
        p
        for p in sorted(source_dir.rglob("*"))
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS and not p.name.startswith(".")
    ]
    return files


def load_and_chunk_directory(
    source_dir: Path,
    chunk_size: int = 512,
    chunk_overlap: int = 50,
) -> list[DocumentChunk]:
    counter = TokenCounter()
    all_chunks: list[DocumentChunk] = []

    for file_path in iter_source_files(source_dir):
        rel_path = str(file_path.relative_to(source_dir))
        raw_text = extract_text_from_file(file_path)
        pieces = chunk_text_paragraph_first(
            raw_text,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            counter=counter,
        )
        for idx, piece in enumerate(pieces):
            all_chunks.append(
                DocumentChunk(
                    text=piece,
                    source_file=rel_path,
                    chunk_id=idx,
                )
            )
    return all_chunks
