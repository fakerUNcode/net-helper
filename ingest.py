from __future__ import annotations

import argparse
import sys
from pathlib import Path

import chromadb

from rag.chunker import load_and_chunk_directory
from rag.config import load_config, resolve_project_path
from rag.embeddings import EmbeddingClient


def ingest(config_path: Path | None = None, rebuild: bool = True) -> None:
    config = load_config(config_path)
    source_dir = resolve_project_path(config["docs"]["source_dir"])
    persist_dir = resolve_project_path(config["vector_store"]["persist_directory"])
    collection_name = config["vector_store"].get("collection_name", "private_kb")

    chunk_size = int(config["chunking"].get("chunk_size", 512))
    chunk_overlap = int(config["chunking"].get("chunk_overlap", 50))

    if not source_dir.exists():
        print(f"[Error] Missing directory: {source_dir}", file=sys.stderr)
        sys.exit(1)

    chunks = load_and_chunk_directory(
        source_dir=source_dir,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    if not chunks:
        print("[Error] No PDF / Markdown / TXT files found.", file=sys.stderr)
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest documents into ChromaDB")
    parser.add_argument("--config", type=Path, default=None, help="Config path")
    parser.add_argument(
        "--append",
        action="store_true",
        help="Append instead of rebuilding",
    )
    args = parser.parse_args()
    ingest(config_path=args.config, rebuild=not args.append)


if __name__ == "__main__":
    main()
