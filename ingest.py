from __future__ import annotations

import argparse
from dataclasses import dataclass
import sys
from pathlib import Path

import chromadb

from rag.chunker import load_and_chunk_directory_with_report
from rag.config import load_config, resolve_project_path
from rag.embeddings import EmbeddingClient
from rag.manifest import check_index_status, write_index_manifest


@dataclass(slots=True)
class IngestResult:
    indexed_files: int
    total_chunks: int
    skipped_duplicates: list[tuple[str, str]]
    skipped_empty: list[str]
    skipped_because_fresh: bool = False


def ingest(
    config_path: Path | None = None,
    rebuild: bool = True,
    if_stale: bool = False,
) -> IngestResult:
    config = load_config(config_path)
    source_dir = resolve_project_path(config["docs"]["source_dir"])
    persist_dir = resolve_project_path(config["vector_store"]["persist_directory"])
    collection_name = config["vector_store"].get("collection_name", "private_kb")

    if if_stale:
        status = check_index_status(config)
        existing_count = 0
        if persist_dir.exists():
            try:
                client = chromadb.PersistentClient(path=str(persist_dir))
                col = client.get_or_create_collection(
                    name=collection_name,
                    metadata={"hnsw:space": "cosine"},
                )
                existing_count = col.count()
            except Exception:
                existing_count = 0
        if not status.needs_rebuild and existing_count > 0:
            print(f"[NetHelper] Vector index up to date ({existing_count} chunks).")
            return IngestResult(
                indexed_files=0,
                total_chunks=existing_count,
                skipped_duplicates=[],
                skipped_empty=[],
                skipped_because_fresh=True,
            )
        print(f"[NetHelper] Rebuilding index: {status.reason}")

    chunk_size = int(config["chunking"].get("chunk_size", 512))
    chunk_overlap = int(config["chunking"].get("chunk_overlap", 50))

    if not source_dir.exists():
        print(f"[Error] Missing directory: {source_dir}", file=sys.stderr)
        sys.exit(1)

    report = load_and_chunk_directory_with_report(
        source_dir=source_dir,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    for pdf_name, md_name in report.skipped_duplicates:
        print(f"[Skip duplicate PDF] {pdf_name} (covered by {md_name})")
    for empty_name in report.skipped_empty:
        print(f"[Skip empty/scanned file] {empty_name} (no extractable text)", file=sys.stderr)

    chunks = report.chunks
    if not chunks:
        print("[Error] No extractable PDF / Markdown / TXT content found.", file=sys.stderr)
        sys.exit(1)

    embedder = EmbeddingClient(config["embedding"])
    texts = [c.text for c in chunks]
    embeddings = embedder.embed_documents(texts, batch_size=32)

    persist_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(persist_dir))

    if rebuild:
        try:
            client.delete_collection(name=collection_name)
        except Exception:
            pass

    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )

    ids = [f"{c.source_file}::chunk_{c.chunk_id}" for c in chunks]
    metadatas = [{"source_file": c.source_file, "chunk_id": c.chunk_id} for c in chunks]

    batch_size = 128
    for start in range(0, len(chunks), batch_size):
        end = start + batch_size
        collection.upsert(
            ids=ids[start:end],
            documents=texts[start:end],
            embeddings=embeddings[start:end],
            metadatas=metadatas[start:end],
        )

    summary = {
        "indexed_files": len(report.indexed_files),
        "total_chunks": len(chunks),
        "skipped_duplicates": [pdf for pdf, _ in report.skipped_duplicates],
        "skipped_empty": report.skipped_empty,
    }
    write_index_manifest(config, summary=summary)
    print(f"[NetHelper] Indexed {len(report.indexed_files)} files ({len(chunks)} chunks) -> {persist_dir}")

    return IngestResult(
        indexed_files=len(report.indexed_files),
        total_chunks=len(chunks),
        skipped_duplicates=report.skipped_duplicates,
        skipped_empty=report.skipped_empty,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest documents into ChromaDB")
    parser.add_argument("--config", type=Path, default=None, help="Config path")
    parser.add_argument(
        "--append",
        action="store_true",
        help="Append instead of rebuilding",
    )
    parser.add_argument(
        "--if-stale",
        action="store_true",
        help="Only rebuild when docs or config changed",
    )
    args = parser.parse_args()
    ingest(config_path=args.config, rebuild=not args.append, if_stale=args.if_stale)


if __name__ == "__main__":
    main()
