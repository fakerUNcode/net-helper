from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from typing import Any

import requests

from rag.config import resolve_project_path


class LocalLLMClient:
    """本地 LLM 流式缓冲客户端：生成过程中所有 token 仅写入内存 buffer，仅在生成结束(stop)后一次性返回。"""

    def __init__(self, llm_cfg: dict[str, Any]) -> None:
        self.cfg = llm_cfg
        self.provider = str(llm_cfg.get("provider", "ollama")).lower()
        self._llama_instance = None

    def generate_complete(self, messages: list[dict[str, str]]) -> str:
        if self.provider == "ollama":
            return self._generate_ollama_buffered(messages)
        if self.provider == "llama_cpp":
            return self._generate_llama_cpp_buffered(messages)
        raise ValueError(f"不支持的 LLM provider: {self.provider}")

    def _generate_ollama_buffered(self, messages: list[dict[str, str]]) -> str:
        base_url = str(self.cfg.get("ollama_base_url", "http://127.0.0.1:11434")).rstrip("/")
        model = str(self.cfg.get("ollama_model", "qwen2.5:3b"))
        timeout = int(self.cfg.get("timeout_seconds", 120))

        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": float(self.cfg.get("temperature", 0.1)),
                "num_predict": int(self.cfg.get("max_tokens", 1024)),
            },
        }

        token_buffer: list[str] = []
        finished_with_stop = False

        try:
            with requests.post(
                f"{base_url}/api/chat",
                json=payload,
                stream=True,
                timeout=timeout,
            ) as resp:
                resp.raise_for_status()
                for raw_line in resp.iter_lines(decode_unicode=True):
                    if not raw_line:
                        continue
                    data = json.loads(raw_line)
                    if "error" in data:
                        raise RuntimeError(f"Ollama 返回错误: {data['error']}")

                    content = (data.get("message") or {}).get("content", "")
                    if content:
                        # 流式隐藏：token 仅写入内存缓冲区，不向 UI 输出
                        token_buffer.append(content)

                    # 生成结束检测器
                    if data.get("done") is True:
                        done_reason = data.get("done_reason", "stop")
                        if done_reason in ("stop", "length", None, ""):
                            finished_with_stop = True
                        break
        except requests.RequestException as exc:
            raise RuntimeError(
                f"无法连接本地 Ollama 服务 ({base_url})，请确认已启动 Ollama 并拉取模型 `{model}`。\n详情: {exc}"
            ) from exc

        if not finished_with_stop:
            raise RuntimeError("模型流式生成异常中断，未检测到结束信号 (done/stop)。")

        return "".join(token_buffer)

    def _resolve_llama_cpp_params(self) -> tuple[str, int, int]:
        profiles = self.cfg.get("profiles") or {}
        profile_key = str(self.cfg.get("model_profile", "3b"))
        profile = profiles.get(profile_key) or {}

        raw_path = profile.get("model_path") or self.cfg.get(
            "llama_cpp_model_path", "./models/qwen2.5-3b-instruct-q4_k_m.gguf"
        )
        n_ctx = int(profile.get("n_ctx", self.cfg.get("llama_cpp_n_ctx", 4096)))
        n_gpu_layers = int(profile.get("n_gpu_layers", self.cfg.get("llama_cpp_n_gpu_layers", -1)))
        return str(raw_path), n_ctx, n_gpu_layers

    def _prepare_windows_cuda_dlls(self) -> None:
        if sys.platform != "win32":
            return
        candidate_dirs: list[Path] = []
        for entry in sys.path:
            if not entry:
                continue
            sp = Path(entry)
            nvidia_dir = sp / "nvidia"
            if nvidia_dir.is_dir():
                for bin_dir in nvidia_dir.glob("*/bin"):
                    if bin_dir.is_dir():
                        candidate_dirs.append(bin_dir)
            torch_lib = sp / "torch" / "lib"
            if torch_lib.is_dir():
                candidate_dirs.append(torch_lib)

        seen: set[Path] = set()
        for dll_dir in candidate_dirs:
            resolved = dll_dir.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            try:
                os.add_dll_directory(str(resolved))
            except OSError:
                pass
            path_env = os.environ.get("PATH", "")
            if str(resolved) not in path_env:
                os.environ["PATH"] = f"{resolved}{os.pathsep}{path_env}"

    def _get_llama_cpp(self):
        if self._llama_instance is None:
            self._prepare_windows_cuda_dlls()
            try:
                from llama_cpp import Llama
            except ImportError as exc:
                raise RuntimeError(
                    "未安装 llama-cpp-python，请运行 `pip install llama-cpp-python` 后重试。"
                ) from exc

            raw_path, n_ctx, n_gpu_layers = self._resolve_llama_cpp_params()
            model_path = resolve_project_path(raw_path)
            if not model_path.exists():
                raise FileNotFoundError(
                    f"未找到 GGUF 模型文件: {model_path}\n"
                    f"请将自训练或下载的 Qwen2.5-3B / 7B-Instruct GGUF 模型放入 ./models/ 目录，"
                    f"或在 config.yaml 中修改对应路径。"
                )
            self._llama_instance = Llama(
                model_path=str(model_path),
                n_ctx=n_ctx,
                n_gpu_layers=n_gpu_layers,
                verbose=False,
            )
        return self._llama_instance

    def _generate_llama_cpp_buffered(self, messages: list[dict[str, str]]) -> str:
        llm = self._get_llama_cpp()
        stream = llm.create_chat_completion(
            messages=messages,
            temperature=float(self.cfg.get("temperature", 0.1)),
            max_tokens=int(self.cfg.get("max_tokens", 1024)),
            stream=True,
        )

        token_buffer: list[str] = []
        finish_reason: str | None = None

        for chunk in stream:
            choices = chunk.get("choices") or []
            if not choices:
                continue
            choice = choices[0]
            delta = choice.get("delta") or {}
            content = delta.get("content")
            if content:
                # 流式隐藏：token 仅写入内存缓冲区，不向 UI 输出
                token_buffer.append(content)
            if choice.get("finish_reason") is not None:
                finish_reason = choice.get("finish_reason")
                if finish_reason in ("stop", "length"):
                    break

        if finish_reason not in ("stop", "length"):
            raise RuntimeError(f"llama.cpp 生成未正常结束，finish_reason={finish_reason!r}")

        return "".join(token_buffer)
