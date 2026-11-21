from __future__ import annotations

import os
from typing import Any


class EmbeddingClient:
    """统一嵌入接口：支持本地 bge-small-zh-v1.5 与 OpenAI text-embedding-3-small。"""

    def __init__(self, embedding_cfg: dict[str, Any]) -> None:
        self.cfg = embedding_cfg
        self.provider = str(embedding_cfg.get("provider", "local")).lower()
        self._local_model = None
        self._openai_client = None

    def _get_local_model(self):
        if self._local_model is None:
            from sentence_transformers import SentenceTransformer

            from rag.config import resolve_project_path

            model_name = str(self.cfg.get("local_model", "BAAI/bge-small-zh-v1.5"))
            device = self.cfg.get("local_device", "auto")
            if device == "auto":
                device = None

            local_bundle = resolve_project_path("./models/bge-small-zh-v1.5")
            if local_bundle.exists() and any(local_bundle.iterdir()):
                os.environ.setdefault("HF_HUB_OFFLINE", "1")
                os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
                self._local_model = SentenceTransformer(
                    str(local_bundle),
                    device=device,
                    local_files_only=True,
                )
            else:
                self._local_model = SentenceTransformer(model_name, device=device)
        return self._local_model

    def _get_openai_client(self):
        if self._openai_client is None:
            from openai import OpenAI

            env_name = self.cfg.get("openai_api_key_env", "OPENAI_API_KEY")
            api_key = os.environ.get(env_name, "")
            if not api_key:
                raise RuntimeError(f"未检测到环境变量 {env_name}，无法调用 OpenAI Embedding API。")
            base_url = self.cfg.get("openai_base_url", "https://api.openai.com/v1")
            self._openai_client = OpenAI(api_key=api_key, base_url=base_url)
        return self._openai_client

    def embed_documents(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        if not texts:
            return []
        if self.provider == "openai":
            client = self._get_openai_client()
            model = self.cfg.get("openai_model", "text-embedding-3-small")
            vectors: list[list[float]] = []
            for i in range(0, len(texts), batch_size):
                batch = texts[i : i + batch_size]
                resp = client.embeddings.create(model=model, input=batch)
                vectors.extend([item.embedding for item in resp.data])
            return vectors

        model = self._get_local_model()
        arr = model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return arr.tolist()

    def embed_query(self, query: str) -> list[float]:
        if self.provider == "openai":
            return self.embed_documents([query])[0]

        model = self._get_local_model()
        model_name = str(self.cfg.get("local_model", "")).lower()
        # BGE 中文检索模型推荐为查询添加检索前缀
        text = f"为这个句子生成表示以用于检索相关文章：{query}" if "bge" in model_name else query
        arr = model.encode(
            [text],
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return arr[0].tolist()
