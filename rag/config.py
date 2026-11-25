from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
from typing import Any

import yaml


def _detect_project_root() -> Path:
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        if exe_dir.name == "MacOS" and exe_dir.parent.name == "Contents":
            bundle_parent = exe_dir.parents[2]
            if (bundle_parent / "config.yaml").exists():
                return bundle_parent
        return exe_dir
    return Path(__file__).resolve().parent.parent


PROJECT_ROOT = _detect_project_root()
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config.yaml"

DEFAULT_CONFIG: dict[str, Any] = {
    "app": {
        "name": "NetHelper",
        "hotkey": "<ctrl>+<shift>+h",
        "theme": "sepia",
        "window_opacity": 0.70,
        "input_width": 360,
        "input_height": 60,
        "answer_width": 360,
        "answer_max_height": 117,
        "margin_x": 24,
        "margin_y": 24,
    },
    "docs": {
        "source_dir": "./docs",
    },
    "vector_store": {
        "persist_directory": "./vector_store",
        "collection_name": "private_kb",
        "top_k": 5,
    },
    "chunking": {
        "chunk_size": 512,
        "chunk_overlap": 50,
    },
    "embedding": {
        "provider": "local",
        "local_model": "BAAI/bge-small-zh-v1.5",
        "local_device": "auto",
        "openai_model": "text-embedding-3-small",
        "openai_api_key_env": "OPENAI_API_KEY",
        "openai_base_url": "https://api.openai.com/v1",
    },
    "llm": {
        "provider": "llama_cpp",
        "model_profile": "3b",
        "profiles": {
            "3b": {
                "label": "3b",
                "model_path": "./models/qwen2.5-3b-instruct-q4_k_m.gguf",
                "n_ctx": 4096,
                "n_gpu_layers": -1,
            },
            "7b": {
                "label": "7b",
                "model_path": "./models/qwen2.5-7b-instruct-q4_k_m.gguf",
                "n_ctx": 4096,
                "n_gpu_layers": -1,
            },
            "8b": {
                "label": "8b (Qwen3-8B)",
                "model_path": "./models/qwen3-8b-q4_k_m.gguf",
                "n_ctx": 6144,
                "n_gpu_layers": -1,
                "temperature": 0.6,
                "top_p": 0.95,
                "top_k": 20,
                "max_tokens": 3072,
            },
            "14b": {
                "label": "14b (Qwen3-14B)",
                "model_path": "./models/qwen3-14b-q4_k_m.gguf",
                "n_ctx": 6144,
                "n_gpu_layers": -1,
                "temperature": 0.6,
                "top_p": 0.95,
                "top_k": 20,
                "max_tokens": 3072,
            },
        },
        "llama_cpp_model_path": "./models/qwen2.5-3b-instruct-q4_k_m.gguf",
        "llama_cpp_n_ctx": 4096,
        "llama_cpp_n_gpu_layers": -1,
        "ollama_base_url": "http://127.0.0.1:11434",
        "ollama_model": "qwen2.5:3b",
        "temperature": 0.1,
        "max_tokens": 1024,
        "timeout_seconds": 120,
    },
}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def resolve_project_path(raw_path: str | Path) -> Path:
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = (PROJECT_ROOT / path).resolve()
    return path


def load_config(config_path: str | Path | None = None) -> dict[str, Any]:
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    if not path.exists():
        return deepcopy(DEFAULT_CONFIG)
    with path.open("r", encoding="utf-8") as f:
        loaded = yaml.safe_load(f) or {}
    return _deep_merge(DEFAULT_CONFIG, loaded)


def save_config(config: dict[str, Any], config_path: str | Path | None = None) -> None:
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(config, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
