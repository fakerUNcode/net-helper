from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

import requests

from rag.config import resolve_project_path

ProgressCallback = Callable[[int, int, str], None]

GGUF_URLS: dict[str, list[str]] = {
    "3b": [
        "https://hf-mirror.com/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf",
        "https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf",
    ],
    "7b": [
        "https://hf-mirror.com/bartowski/Qwen2.5-7B-Instruct-GGUF/resolve/main/Qwen2.5-7B-Instruct-Q4_K_M.gguf",
        "https://huggingface.co/bartowski/Qwen2.5-7B-Instruct-GGUF/resolve/main/Qwen2.5-7B-Instruct-Q4_K_M.gguf",
    ],
    "8b": [
        "https://hf-mirror.com/Qwen/Qwen3-8B-GGUF/resolve/main/Qwen3-8B-Q4_K_M.gguf",
        "https://huggingface.co/Qwen/Qwen3-8B-GGUF/resolve/main/Qwen3-8B-Q4_K_M.gguf",
        "https://hf-mirror.com/bartowski/Qwen_Qwen3-8B-GGUF/resolve/main/Qwen_Qwen3-8B-Q4_K_M.gguf",
        "https://huggingface.co/bartowski/Qwen_Qwen3-8B-GGUF/resolve/main/Qwen_Qwen3-8B-Q4_K_M.gguf",
    ],
    "14b": [
        "https://hf-mirror.com/Qwen/Qwen3-14B-GGUF/resolve/main/Qwen3-14B-Q4_K_M.gguf",
        "https://huggingface.co/Qwen/Qwen3-14B-GGUF/resolve/main/Qwen3-14B-Q4_K_M.gguf",
        "https://hf-mirror.com/bartowski/Qwen_Qwen3-14B-GGUF/resolve/main/Qwen_Qwen3-14B-Q4_K_M.gguf",
        "https://huggingface.co/bartowski/Qwen_Qwen3-14B-GGUF/resolve/main/Qwen_Qwen3-14B-Q4_K_M.gguf",
    ],
}

MATHJAX_FILES: dict[str, str] = {
    "es5/tex-mml-chtml.js": "https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js",
}


def download_file_with_resume(
    urls: list[str],
    dest_path: Path,
    progress_cb: ProgressCallback | None = None,
    label: str = "",
) -> Path:
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    part_path = dest_path.with_suffix(dest_path.suffix + ".part")

    last_err: Exception | None = None
    for url in urls:
        try:
            existing_size = part_path.stat().st_size if part_path.exists() else 0
            headers = {"Range": f"bytes={existing_size}-"} if existing_size > 0 else {}
            with requests.get(url, stream=True, headers=headers, timeout=30) as resp:
                if resp.status_code == 416:
                    existing_size = 0
                    part_path.unlink(missing_ok=True)
                    resp2 = requests.get(url, stream=True, timeout=30)
                    resp2.raise_for_status()
                    resp = resp2
                elif resp.status_code == 200 and existing_size > 0:
                    existing_size = 0
                else:
                    resp.raise_for_status()

                content_len = int(resp.headers.get("Content-Length", "0") or 0)
                total_size = existing_size + content_len if content_len > 0 else 0
                downloaded = existing_size
                mode = "ab" if existing_size > 0 and resp.status_code == 206 else "wb"

                with part_path.open(mode) as f:
                    for chunk in resp.iter_content(chunk_size=1024 * 512):
                        if not chunk:
                            continue
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_cb:
                            progress_cb(downloaded, total_size, label or dest_path.name)

            part_path.replace(dest_path)
            return dest_path
        except Exception as exc:
            last_err = exc
            continue

    raise RuntimeError(f"Download failed ({dest_path.name}): {last_err}")


def ensure_offline_mathjax(progress_cb: ProgressCallback | None = None) -> Path:
    assets_dir = resolve_project_path("./assets/mathjax")
    target = assets_dir / "es5" / "tex-mml-chtml.js"
    if target.exists():
        return target
    if progress_cb:
        progress_cb(0, 0, "MathJax")
    return download_file_with_resume(
        [MATHJAX_FILES["es5/tex-mml-chtml.js"]],
        target,
        progress_cb=progress_cb,
        label="MathJax",
    )


def ensure_offline_embedding(progress_cb: ProgressCallback | None = None) -> Path:
    target_dir = resolve_project_path("./models/bge-small-zh-v1.5")
    if target_dir.exists() and (target_dir / "modules.json").exists():
        return target_dir

    if progress_cb:
        progress_cb(0, 0, "Embedding")

    from huggingface_hub import snapshot_download

    target_dir.mkdir(parents=True, exist_ok=True)
    for endpoint in ("https://hf-mirror.com", "https://huggingface.co"):
        try:
            os.environ["HF_ENDPOINT"] = endpoint
            snapshot_download(
                repo_id="BAAI/bge-small-zh-v1.5",
                local_dir=str(target_dir),
            )
            return target_dir
        except Exception:
            continue

    raise RuntimeError("Embedding download failed.")


def ensure_offline_gguf(profile_key: str, dest_path: Path, progress_cb: ProgressCallback | None = None) -> Path:
    if dest_path.exists():
        return dest_path
    urls = GGUF_URLS.get(profile_key)
    if not urls:
        raise ValueError(f"Unknown model profile: {profile_key}")
    return download_file_with_resume(
        urls,
        dest_path,
        progress_cb=progress_cb,
        label=profile_key,
    )


def check_offline_readiness(gguf_path: Path) -> dict[str, bool]:
    mathjax_ok = resolve_project_path("./assets/mathjax/es5/tex-mml-chtml.js").exists()
    embed_dir = resolve_project_path("./models/bge-small-zh-v1.5")
    embed_ok = embed_dir.exists() and (embed_dir / "modules.json").exists()
    gguf_ok = gguf_path.exists()
    return {
        "gguf": gguf_ok,
        "embedding": embed_ok,
        "mathjax": mathjax_ok,
        "all_ready": gguf_ok and embed_ok and mathjax_ok,
    }
