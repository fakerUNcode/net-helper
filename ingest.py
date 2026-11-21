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
        print(f"[错误] 资料库目录不存在: {source_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"[1/4] 正在扫描并切分资料库: {source_dir} (chunk_size={chunk_size}, overlap={chunk_overlap})")
    chunks = load_and_chunk_directory(
        source_dir=source_dir,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    if not chunks:
        print("[警告] 未在资料库目录中找到有效的 PDF / Markdown / TXT 文本内容。")
        sys.exit(1)

    print(f"[2/4] 共生成 {len(chunks)} 个文本块，正在初始化嵌入模型 ({config['embedding']['provider']})...")
    embedder = EmbeddingClient(config["embedding"])
    texts = [c.text for c in chunks]
    embeddings = embedder.embed_documents(texts, batch_size=32)

    print(f"[3/4] 正在写入 ChromaDB 向量库: {persist_dir} (collection={collection_name}, space=cosine)")
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

    print(f"[4/4] 入库完成！当前向量库总片段数: {collection.count()}")


def main() -> None:
    parser = argparse.ArgumentParser(description="将私有资料库 (PDF/MD/TXT) 切片并入库到 ChromaDB。")
    parser.add_argument("--config", type=Path, default=None, help="配置文件路径 (默认 ./config.yaml)")
    parser.add_argument(
        "--append",
        action="store_true",
        help="增量更新模式（默认会先清空旧集合再重建索引）",
    )
    args = parser.parse_args()
    ingest(config_path=args.config, rebuild=not args.append)


if __name__ == "__main__":
    main()
