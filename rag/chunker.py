from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

SUPPORTED_EXTENSIONS = {".pdf", ".md", ".markdown", ".txt"}
MARKDOWN_EXTENSIONS = {".md", ".markdown"}
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_FENCE_RE = re.compile(r"^\s*(```+|~~~+)")
_TABLE_SEP_RE = re.compile(r"^\s*\|?(?:\s*:?-+:?\s*\|)+\s*:?-+:?\s*\|?\s*$")
_MIN_STANDALONE_SECTION_TOKENS = 100


@dataclass(slots=True)
class DocumentChunk:
    text: str
    source_file: str
    chunk_id: int


@dataclass(slots=True)
class SourceScanResult:
    files_to_index: list[Path]
    skipped_duplicates: list[tuple[Path, Path]]
    all_candidate_files: list[Path]


@dataclass(slots=True)
class ChunkDirectoryReport:
    chunks: list[DocumentChunk] = field(default_factory=list)
    indexed_files: list[str] = field(default_factory=list)
    skipped_duplicates: list[tuple[str, str]] = field(default_factory=list)
    skipped_empty: list[str] = field(default_factory=list)


class TokenCounter:
    """优先使用 tiktoken，离线无缓存时自动回退到中英文词元估算；严格保证 UTF-8 字符边界不截断。"""

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
        tokens = re.findall(r"[\u4e00-\u9fff]|[A-Za-z0-9_]+|[^\s\w]", text)
        return len(tokens)

    @staticmethod
    def _advance_utf8_start(token_bytes: list[bytes], idx: int, limit: int) -> int:
        while idx < limit and token_bytes[idx] and (token_bytes[idx][0] & 0xC0) == 0x80:
            idx += 1
        return idx

    @staticmethod
    def _decode_utf8_safe_slice(token_bytes: list[bytes], start: int, end: int) -> tuple[str, int]:
        cur_end = end
        while cur_end > start + 1:
            try:
                return b"".join(token_bytes[start:cur_end]).decode("utf-8"), cur_end
            except UnicodeDecodeError:
                cur_end -= 1
        return b"".join(token_bytes[start:cur_end]).decode("utf-8", errors="ignore"), cur_end

    def tail_by_tokens(self, text: str, max_tokens: int) -> str:
        if max_tokens <= 0 or not text:
            return ""
        if self._encoding is not None:
            ids = self._encoding.encode(text, disallowed_special=())
            if len(ids) <= max_tokens:
                return text
            token_bytes = self._encoding.decode_tokens_bytes(ids[-max_tokens:])
            start = self._advance_utf8_start(token_bytes, 0, len(token_bytes))
            while start < len(token_bytes):
                try:
                    return b"".join(token_bytes[start:]).decode("utf-8").lstrip()
                except UnicodeDecodeError:
                    start += 1
            return b"".join(token_bytes).decode("utf-8", errors="ignore").lstrip()

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
            token_bytes = self._encoding.decode_tokens_bytes(ids)
            n = len(ids)
            pieces: list[str] = []
            start = 0
            while start < n:
                start = self._advance_utf8_start(token_bytes, start, n)
                if start >= n:
                    break
                raw_end = min(n, start + chunk_size)
                sub, actual_end = self._decode_utf8_safe_slice(token_bytes, start, raw_end)
                sub = sub.strip()
                if sub:
                    pieces.append(sub)
                if actual_end >= n:
                    break
                next_start = max(start + 1, actual_end - overlap)
                next_start = self._advance_utf8_start(token_bytes, next_start, actual_end)
                start = next_start if next_start < actual_end else actual_end
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
        try:
            import pymupdf
        except ImportError:
            import fitz as pymupdf  # type: ignore[no-redef]

        pages: list[str] = []
        with pymupdf.open(file_path) as doc:
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


def _pack_units(
    units: list[str],
    chunk_size: int,
    chunk_overlap: int,
    counter: TokenCounter,
    *,
    allow_overlap: bool = True,
) -> list[str]:
    chunks: list[str] = []
    current_parts: list[str] = []
    current_tokens = 0

    for unit in units:
        unit_tokens = counter.count(unit)
        if not current_parts:
            current_parts.append(unit)
            current_tokens = unit_tokens
            continue

        if current_tokens + unit_tokens + 1 <= chunk_size:
            current_parts.append(unit)
            current_tokens += unit_tokens + 1
        else:
            finished_chunk = "\n\n".join(current_parts).strip()
            if finished_chunk:
                chunks.append(finished_chunk)

            if allow_overlap and chunk_overlap > 0:
                last_line = finished_chunk.splitlines()[-1].lstrip() if finished_chunk else ""
                is_table_boundary = last_line.startswith("|") or unit.lstrip().startswith("|")
                is_code_boundary = finished_chunk.rstrip().endswith("```") or unit.lstrip().startswith("```")
                if not is_table_boundary and not is_code_boundary:
                    overlap_text = counter.tail_by_tokens(finished_chunk, chunk_overlap)
                    if overlap_text and counter.count(overlap_text) + unit_tokens + 1 <= chunk_size:
                        current_parts = [overlap_text, unit]
                        current_tokens = counter.count(overlap_text) + unit_tokens + 1
                        continue

            current_parts = [unit]
            current_tokens = unit_tokens

    if current_parts:
        last_chunk = "\n\n".join(current_parts).strip()
        if last_chunk:
            chunks.append(last_chunk)

    return chunks


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

    return _pack_units(units, chunk_size, chunk_overlap, counter, allow_overlap=True)


@dataclass(slots=True)
class _MarkdownSection:
    level: int
    heading: str
    parent_tuple: tuple[str, ...]
    body: str


def _parse_markdown_sections(text: str) -> list[_MarkdownSection]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")

    sections: list[_MarkdownSection] = []
    heading_stack: list[tuple[int, str]] = []
    current_level = 0
    current_heading = ""
    current_parents: tuple[str, ...] = ()
    current_lines: list[str] = []

    in_fence = False
    fence_char = ""
    fence_len = 0

    for line in lines:
        fence_match = _FENCE_RE.match(line)
        if fence_match:
            marker = fence_match.group(1)
            if not in_fence:
                in_fence = True
                fence_char = marker[0]
                fence_len = len(marker)
            elif marker[0] == fence_char and len(marker) >= fence_len and line.strip() == marker:
                in_fence = False
                fence_char = ""
                fence_len = 0
            current_lines.append(line)
            continue

        if not in_fence:
            h_match = _HEADING_RE.match(line)
            if h_match:
                body = "\n".join(current_lines).strip()
                if body or current_heading:
                    sections.append(
                        _MarkdownSection(
                            level=current_level,
                            heading=current_heading,
                            parent_tuple=current_parents,
                            body=body,
                        )
                    )
                lvl = len(h_match.group(1))
                while heading_stack and heading_stack[-1][0] >= lvl:
                    heading_stack.pop()
                current_parents = tuple(h for _, h in heading_stack)
                current_level = lvl
                current_heading = line.strip()
                heading_stack.append((lvl, current_heading))
                current_lines = []
                continue

        current_lines.append(line)

    tail_body = "\n".join(current_lines).strip()
    if tail_body or current_heading:
        sections.append(
            _MarkdownSection(
                level=current_level,
                heading=current_heading,
                parent_tuple=current_parents,
                body=tail_body,
            )
        )

    return sections


def _clean_section_body(body: str) -> str:
    lines = body.splitlines()
    while lines and (not lines[0].strip() or lines[0].strip() == "---"):
        lines.pop(0)
    while lines and (not lines[-1].strip() or lines[-1].strip() == "---"):
        lines.pop()
    return "\n".join(lines).strip()


def _split_markdown_table(table_lines: list[str], budget: int, counter: TokenCounter) -> list[str]:
    if len(table_lines) <= 2:
        joined = "\n".join(table_lines)
        return counter.split_text_by_tokens(joined, budget, overlap=0)

    header = "\n".join(table_lines[:2])
    header_tokens = counter.count(header)
    if header_tokens >= budget:
        return counter.split_text_by_tokens("\n".join(table_lines), budget, overlap=0)

    chunks: list[str] = []
    rows = table_lines[2:]
    current_rows: list[str] = []
    current_tokens = header_tokens

    for row in rows:
        row_tokens = counter.count(row) + 1
        if not current_rows:
            if header_tokens + row_tokens <= budget:
                current_rows.append(row)
                current_tokens = header_tokens + row_tokens
            else:
                chunks.extend(counter.split_text_by_tokens(f"{header}\n{row}", budget, overlap=0))
            continue

        if current_tokens + row_tokens <= budget:
            current_rows.append(row)
            current_tokens += row_tokens
        else:
            chunks.append(f"{header}\n" + "\n".join(current_rows))
            if header_tokens + row_tokens <= budget:
                current_rows = [row]
                current_tokens = header_tokens + row_tokens
            else:
                chunks.extend(counter.split_text_by_tokens(f"{header}\n{row}", budget, overlap=0))
                current_rows = []
                current_tokens = header_tokens

    if current_rows:
        chunks.append(f"{header}\n" + "\n".join(current_rows))
    return chunks


def _extract_markdown_blocks(body: str, budget: int, counter: TokenCounter) -> list[str]:
    lines = body.split("\n")
    raw_blocks: list[tuple[str, list[str]]] = []
    idx = 0
    n = len(lines)

    while idx < n:
        line = lines[idx]
        if not line.strip():
            idx += 1
            continue

        fence_match = _FENCE_RE.match(line)
        if fence_match:
            marker = fence_match.group(1)
            fence_char = marker[0]
            fence_len = len(marker)
            block = [line]
            idx += 1
            while idx < n:
                block.append(lines[idx])
                close_match = _FENCE_RE.match(lines[idx])
                if (
                    close_match
                    and close_match.group(1)[0] == fence_char
                    and len(close_match.group(1)) >= fence_len
                    and lines[idx].strip() == close_match.group(1)
                ):
                    idx += 1
                    break
                idx += 1
            raw_blocks.append(("code", block))
            continue

        if line.lstrip().startswith("|") and idx + 1 < n and _TABLE_SEP_RE.match(lines[idx + 1]):
            block = [line, lines[idx + 1]]
            idx += 2
            while idx < n and lines[idx].lstrip().startswith("|"):
                block.append(lines[idx])
                idx += 1
            raw_blocks.append(("table", block))
            continue

        para_lines: list[str] = []
        while idx < n and lines[idx].strip():
            if _FENCE_RE.match(lines[idx]):
                break
            if lines[idx].lstrip().startswith("|") and idx + 1 < n and _TABLE_SEP_RE.match(lines[idx + 1]):
                break
            para_lines.append(lines[idx])
            idx += 1
        if para_lines:
            raw_blocks.append(("para", para_lines))

    units: list[str] = []
    for kind, block_lines in raw_blocks:
        block_text = "\n".join(block_lines).strip()
        if not block_text:
            continue
        if counter.count(block_text) <= budget:
            units.append(block_text)
            continue

        if kind == "table":
            units.extend(_split_markdown_table(block_lines, budget, counter))
        elif kind == "code":
            units.extend(counter.split_text_by_tokens(block_text, budget, overlap=0))
        else:
            units.extend(_split_long_paragraph(block_text, counter, budget, overlap=0))

    return units


def _split_oversized_section(
    heading: str,
    body: str,
    chunk_size: int,
    chunk_overlap: int,
    counter: TokenCounter,
) -> list[str]:
    cont_heading = f"{heading}（续）" if heading else ""
    prefix_tokens = counter.count(cont_heading) + 2 if cont_heading else 0
    body_budget = max(64, chunk_size - prefix_tokens)

    units = _extract_markdown_blocks(body, body_budget, counter)
    if not units:
        return [heading] if heading else []

    body_chunks = _pack_units(
        units,
        chunk_size=body_budget,
        chunk_overlap=min(chunk_overlap, body_budget // 4),
        counter=counter,
        allow_overlap=True,
    )

    result: list[str] = []
    for i, chunk_body in enumerate(body_chunks):
        if i == 0:
            candidate = f"{heading}\n\n{chunk_body}".strip() if heading else chunk_body
            if counter.count(candidate) <= chunk_size:
                result.append(candidate)
            else:
                # 若首块加上标题略超 chunk_size，回退按完整前缀重新切分
                first_budget = max(64, chunk_size - (counter.count(heading) + 2 if heading else 0))
                sub_units = _extract_markdown_blocks(chunk_body, first_budget, counter)
                for j, sub in enumerate(_pack_units(sub_units, first_budget, 0, counter, allow_overlap=False)):
                    hdr = heading if j == 0 else cont_heading
                    result.append(f"{hdr}\n\n{sub}".strip() if hdr else sub)
        else:
            result.append(f"{cont_heading}\n\n{chunk_body}".strip() if cont_heading else chunk_body)
    return result


def chunk_text_markdown(
    text: str,
    chunk_size: int = 512,
    chunk_overlap: int = 50,
    counter: TokenCounter | None = None,
) -> list[str]:
    """按 Markdown 标题边界切分，保持每道题/小节与表格/代码块完整；超长章节在续块保留标题上下文。"""
    if not text or not text.strip():
        return []

    counter = counter or TokenCounter()
    raw_sections = _parse_markdown_sections(text)
    if not raw_sections:
        return chunk_text_paragraph_first(text, chunk_size=chunk_size, chunk_overlap=chunk_overlap, counter=counter)

    cleaned: list[_MarkdownSection] = []
    for sec in raw_sections:
        body = _clean_section_body(sec.body)
        if not body:
            continue
        cleaned.append(
            _MarkdownSection(
                level=sec.level,
                heading=sec.heading,
                parent_tuple=sec.parent_tuple,
                body=body,
            )
        )

    if not cleaned:
        return []

    # 合并极短小节：
    # 1) 极短父章节导语（<100 token）若能与紧随其后的子章节整体放入 chunk_size，则合并（保留章节背景）
    # 2) 同级连续极短小节（各自 <100 token）合并至不超过 chunk_size
    merged: list[tuple[str, str, int, tuple[str, ...]]] = []  # (heading, full_text, level, parents)
    i = 0
    while i < len(cleaned):
        sec = cleaned[i]
        full_text = f"{sec.heading}\n\n{sec.body}".strip() if sec.heading else sec.body
        tok = counter.count(full_text)

        if tok < _MIN_STANDALONE_SECTION_TOKENS and i + 1 < len(cleaned):
            nxt = cleaned[i + 1]
            nxt_text = f"{nxt.heading}\n\n{nxt.body}".strip() if nxt.heading else nxt.body
            combined = f"{full_text}\n\n{nxt_text}".strip()
            if nxt.level > sec.level and counter.count(combined) <= chunk_size:
                merged.append((nxt.heading or sec.heading, combined, nxt.level, sec.parent_tuple))
                i += 2
                continue

        if (
            merged
            and tok < _MIN_STANDALONE_SECTION_TOKENS
            and counter.count(merged[-1][1]) < _MIN_STANDALONE_SECTION_TOKENS
            and merged[-1][2] == sec.level
            and merged[-1][3] == sec.parent_tuple
        ):
            combined = f"{merged[-1][1]}\n\n{full_text}".strip()
            if counter.count(combined) <= chunk_size:
                prev_heading, _, prev_lvl, prev_parents = merged[-1]
                merged[-1] = (prev_heading, combined, prev_lvl, prev_parents)
                i += 1
                continue

        merged.append((sec.heading, full_text, sec.level, sec.parent_tuple))
        i += 1

    chunks: list[str] = []
    for heading, full_text, _lvl, _parents in merged:
        if counter.count(full_text) <= chunk_size:
            chunks.append(full_text)
        else:
            # 去掉已拼接在首部的 heading 后对正文分块，确保每块均含标题上下文
            body_only = full_text
            if heading and full_text.startswith(heading):
                body_only = full_text[len(heading) :].lstrip("\n")
            chunks.extend(
                _split_oversized_section(
                    heading=heading,
                    body=body_only,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                    counter=counter,
                )
            )
    return chunks


def scan_source_files(source_dir: Path) -> SourceScanResult:
    if not source_dir.exists():
        return SourceScanResult(files_to_index=[], skipped_duplicates=[], all_candidate_files=[])

    candidates = [
        p
        for p in sorted(source_dir.rglob("*"))
        if (
            p.is_file()
            and p.suffix.lower() in SUPPORTED_EXTENSIONS
            and not p.name.startswith(".")
            and p.name.lower() != "readme.md"
        )
    ]

    md_lookup: dict[tuple[Path, str], Path] = {}
    for p in candidates:
        if p.suffix.lower() in MARKDOWN_EXTENSIONS:
            md_lookup[(p.parent, p.stem.lower())] = p

    files_to_index: list[Path] = []
    skipped_duplicates: list[tuple[Path, Path]] = []
    for p in candidates:
        if p.suffix.lower() == ".pdf":
            sibling_md = md_lookup.get((p.parent, p.stem.lower()))
            if sibling_md is not None:
                skipped_duplicates.append((p, sibling_md))
                continue
        files_to_index.append(p)

    return SourceScanResult(
        files_to_index=files_to_index,
        skipped_duplicates=skipped_duplicates,
        all_candidate_files=candidates,
    )


def iter_source_files(source_dir: Path) -> Iterable[Path]:
    return scan_source_files(source_dir).files_to_index


def load_and_chunk_directory_with_report(
    source_dir: Path,
    chunk_size: int = 512,
    chunk_overlap: int = 50,
) -> ChunkDirectoryReport:
    counter = TokenCounter()
    scan = scan_source_files(source_dir)
    report = ChunkDirectoryReport(
        skipped_duplicates=[
            (str(pdf.relative_to(source_dir)), str(md.relative_to(source_dir)))
            for pdf, md in scan.skipped_duplicates
        ]
    )

    for file_path in scan.files_to_index:
        rel_path = str(file_path.relative_to(source_dir))
        raw_text = extract_text_from_file(file_path)
        if not raw_text or not raw_text.strip():
            report.skipped_empty.append(rel_path)
            continue

        if file_path.suffix.lower() in MARKDOWN_EXTENSIONS:
            pieces = chunk_text_markdown(
                raw_text,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                counter=counter,
            )
        else:
            pieces = chunk_text_paragraph_first(
                raw_text,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                counter=counter,
            )

        if not pieces:
            report.skipped_empty.append(rel_path)
            continue

        report.indexed_files.append(rel_path)
        for idx, piece in enumerate(pieces):
            report.chunks.append(
                DocumentChunk(
                    text=piece,
                    source_file=rel_path,
                    chunk_id=idx,
                )
            )
    return report


def load_and_chunk_directory(
    source_dir: Path,
    chunk_size: int = 512,
    chunk_overlap: int = 50,
) -> list[DocumentChunk]:
    return load_and_chunk_directory_with_report(
        source_dir=source_dir,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    ).chunks
