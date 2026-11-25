from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rag.chunker import scan_source_files
from rag.config import resolve_project_path

MANIFEST_FILENAME = "manifest.json"
CHUNKER_VERSION = 2


@dataclass(slots=True)
class IndexStatus:
    needs_rebuild: bool
    reason: str
    manifest_exists: bool


def _embedding_signature(config: dict[str, Any]) -> dict[str, Any]:
    emb = config.get("embedding") or {}
    provider = str(emb.get("provider", "local")).lower()
    model = emb.get("openai_model", "text-embedding-3-small") if provider == "openai" else emb.get("local_model", "BAAI/bge-small-zh-v1.5")
    return {
        "provider": provider,
        "model": str(model),
    }


def _chunking_signature(config: dict[str, Any]) -> dict[str, int]:
    chk = config.get("chunking") or {}
    return {
        "chunk_size": int(chk.get("chunk_size", 512)),
        "chunk_overlap": int(chk.get("chunk_overlap", 50)),
    }


def build_docs_snapshot(config: dict[str, Any]) -> dict[str, Any]:
    source_dir = resolve_project_path(config["docs"]["source_dir"])
    scan = scan_source_files(source_dir)
    files: dict[str, dict[str, int]] = {}
    for file_path in scan.all_candidate_files:
        rel_path = str(file_path.relative_to(source_dir))
        stat = file_path.stat()
        files[rel_path] = {
            "size": int(stat.st_size),
            "mtime_ns": int(stat.st_mtime_ns),
        }

    return {
        "chunker_version": CHUNKER_VERSION,
        "collection_name": str(config["vector_store"].get("collection_name", "private_kb")),
        "chunking": _chunking_signature(config),
        "embedding": _embedding_signature(config),
        "files": files,
    }


def manifest_path_for_config(config: dict[str, Any]) -> Path:
    persist_dir = resolve_project_path(config["vector_store"]["persist_directory"])
    return persist_dir / MANIFEST_FILENAME


def check_index_status(config: dict[str, Any]) -> IndexStatus:
    manifest_file = manifest_path_for_config(config)
    if not manifest_file.exists():
        return IndexStatus(
            needs_rebuild=True,
            reason="Index manifest missing (initial or legacy index)",
            manifest_exists=False,
        )

    try:
        saved = json.loads(manifest_file.read_text(encoding="utf-8"))
    except Exception:
        return IndexStatus(
            needs_rebuild=True,
            reason="Index manifest corrupted",
            manifest_exists=True,
        )

    current = build_docs_snapshot(config)

    if saved.get("chunker_version") != current["chunker_version"]:
        return IndexStatus(True, "Chunker format upgraded", True)
    if saved.get("collection_name") != current["collection_name"]:
        return IndexStatus(True, "Vector collection changed", True)
    if saved.get("chunking") != current["chunking"]:
        return IndexStatus(True, "Chunking config changed", True)
    if saved.get("embedding") != current["embedding"]:
        return IndexStatus(True, "Embedding config changed", True)

    old_files = saved.get("files") or {}
    new_files = current["files"]

    added = sorted(set(new_files) - set(old_files))
    removed = sorted(set(old_files) - set(new_files))
    modified = sorted(
        k
        for k in set(new_files) & set(old_files)
        if new_files[k] != old_files[k]
    )

    if added or removed or modified:
        parts: list[str] = []
        if added:
            parts.append(f"+{len(added)} added")
        if modified:
            parts.append(f"~{len(modified)} updated")
        if removed:
            parts.append(f"-{len(removed)} removed")
        return IndexStatus(
            needs_rebuild=True,
            reason=f"Documents changed ({', '.join(parts)})",
            manifest_exists=True,
        )

    return IndexStatus(needs_rebuild=False, reason="Up to date", manifest_exists=True)


def write_index_manifest(config: dict[str, Any], summary: dict[str, Any] | None = None) -> Path:
    manifest_file = manifest_path_for_config(config)
    manifest_file.parent.mkdir(parents=True, exist_ok=True)
    payload = build_docs_snapshot(config)
    if summary:
        payload["summary"] = summary
    manifest_file.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return manifest_file
