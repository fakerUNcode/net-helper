from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
VENV_DIR = PROJECT_ROOT / ".venv"
REQ_FILE = PROJECT_ROOT / "requirements.txt"
MARKER_FILE = VENV_DIR / ".deps_installed"


def _venv_python() -> Path:
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def _ensure_venv(reinstall: bool = False) -> Path:
    if sys.version_info < (3, 10):
        print(
            f"[错误] 需要 Python 3.10+，当前版本为 {sys.version_info.major}.{sys.version_info.minor}。",
            file=sys.stderr,
        )
        sys.exit(1)

    py_bin = _venv_python()
    if not py_bin.exists():
        print(f"[1/3] 正在创建虚拟环境: {VENV_DIR}")
        subprocess.run([sys.executable, "-m", "venv", str(VENV_DIR)], check=True)

    if reinstall or not MARKER_FILE.exists():
        print("[2/3] 正在安装/校验项目依赖...")
        subprocess.run([str(py_bin), "-m", "pip", "install", "--upgrade", "pip"], check=True)
        subprocess.run([str(py_bin), "-m", "pip", "install", "-r", str(REQ_FILE)], check=True)
        MARKER_FILE.write_text("ok\n", encoding="utf-8")

    return py_bin


def main() -> int:
    parser = argparse.ArgumentParser(description="一键启动最小完整答案弹窗助手（跨平台）")
    parser.add_argument("--reinstall", action="store_true", help="强制重新安装依赖")
    parser.add_argument("--ingest", action="store_true", help="启动前强制重建知识库向量索引")
    parser.add_argument("--ingest-only", action="store_true", help="仅执行知识库入库，不启动界面")
    parser.add_argument("--model", choices=["3b", "7b"], default=None, help="指定模型版本 (3b 或 7b)")
    parser.add_argument("--skip-hotkey-setup", action="store_true", help="跳过启动前设置弹窗")
    args = parser.parse_args()

    py_bin = _ensure_venv(reinstall=args.reinstall)

    vector_dir = PROJECT_ROOT / "vector_store"
    need_ingest = args.ingest or args.ingest_only or not vector_dir.exists() or not any(vector_dir.iterdir())
    if need_ingest:
        print("[3/3] 正在执行私有资料库入库 (ingest.py)...")
        subprocess.run([str(py_bin), str(PROJECT_ROOT / "ingest.py")], cwd=str(PROJECT_ROOT), check=True)

    if args.ingest_only:
        return 0

    cmd = [str(py_bin), str(PROJECT_ROOT / "main.py")]
    if args.model:
        cmd.extend(["--model", args.model])
    if args.skip_hotkey_setup:
        cmd.append("--skip-hotkey-setup")

    print("[启动] 正在启动最小完整答案弹窗助手...")
    return subprocess.call(cmd, cwd=str(PROJECT_ROOT))


if __name__ == "__main__":
    sys.exit(main())