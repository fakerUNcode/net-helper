from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import chromadb

from rag.config import resolve_project_path
from rag.embeddings import EmbeddingClient


@dataclass(slots=True)
class RetrievedChunk:
    text: str
    source_file: str
    chunk_id: int
    distance: float


class VectorRetriever:
    """基于 ChromaDB 的余弦相似度 Top-K 检索器。"""

    def __init__(self, config: dict[str, Any], embedding_client: EmbeddingClient | None = None) -> None:
        self.config = config
        vs_cfg = config["vector_store"]
        self.persist_dir = resolve_project_path(vs_cfg["persist_directory"])
        self.collection_name = vs_cfg.get("collection_name", "private_kb")
        self.top_k = int(vs_cfg.get("top_k", 3))
        self.embedder = embedding_client or EmbeddingClient(config["embedding"])
        self._client = chromadb.PersistentClient(path=str(self.persist_dir))

    def _get_collection(self):
        return self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def count(self) -> int:
        collection = self._get_collection()
        return collection.count()

    def retrieve(self, query: str, top_k: int | None = None) -> list[RetrievedChunk]:
        collection = self._get_collection()
        total = collection.count()
        if total == 0:
            raise RuntimeError("向量库为空，请先运行 ingest.py 完成私有资料入库。")

        k = min(top_k or self.top_k, total)
        query_vec = self.embedder.embed_query(query)
        results = collection.query(
            query_embeddings=[query_vec],
            n_results=k,
            include=["documents", "metadatas", "distances"],
        )

        docs = (results.get("documents") or [[]])[0]
        metas = (results.get("metadatas") or [[]])[0]
        dists = (results.get("distances") or [[]])[0]

        chunks: list[RetrievedChunk] = []
        for doc, meta, dist in zip(docs, metas, dists):
            meta = meta or {}
            chunks.append(
                RetrievedChunk(
                    text=doc,
                    source_file=str(meta.get("source_file", "unknown")),
                    chunk_id=int(meta.get("chunk_id", -1)),
                    distance=float(dist),
                )
            )
        return chunks
