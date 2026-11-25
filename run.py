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
            f"[Error] Python 3.10+ required (found {sys.version_info.major}.{sys.version_info.minor}).",
            file=sys.stderr,
        )
        sys.exit(1)

    py_bin = _venv_python()
    if not py_bin.exists():
        subprocess.run([sys.executable, "-m", "venv", str(VENV_DIR)], check=True)

    if reinstall or not MARKER_FILE.exists():
        subprocess.run([str(py_bin), "-m", "pip", "install", "-q", "--upgrade", "pip"], check=True)
        subprocess.run([str(py_bin), "-m", "pip", "install", "-q", "-r", str(REQ_FILE)], check=True)
        MARKER_FILE.write_text("ok\n", encoding="utf-8")

    return py_bin


def main() -> int:
    parser = argparse.ArgumentParser(description="NetHelper Launcher")
    parser.add_argument("--reinstall", action="store_true", help="Reinstall dependencies")
    parser.add_argument("--ingest", action="store_true", help="Rebuild index before launch")
    parser.add_argument("--ingest-only", action="store_true", help="Ingest only")
    parser.add_argument("--model", choices=["3b", "7b", "8b", "14b"], default=None, help="Model (3b, 7b, 8b, or 14b)")
    parser.add_argument("--skip-hotkey-setup", action="store_true", help="Skip setup dialog")
    args = parser.parse_args()

    py_bin = _ensure_venv(reinstall=args.reinstall)

    vector_dir = PROJECT_ROOT / "vector_store"
    force_ingest = args.ingest or args.ingest_only or not vector_dir.exists() or not any(vector_dir.iterdir())
    ingest_cmd = [str(py_bin), str(PROJECT_ROOT / "ingest.py")]
    if not force_ingest:
        ingest_cmd.append("--if-stale")
    subprocess.run(ingest_cmd, cwd=str(PROJECT_ROOT), check=True)

    if args.ingest_only:
        return 0

    cmd = [str(py_bin), str(PROJECT_ROOT / "main.py")]
    if args.model:
        cmd.extend(["--model", args.model])
    if args.skip_hotkey_setup:
        cmd.append("--skip-hotkey-setup")

    return subprocess.call(cmd, cwd=str(PROJECT_ROOT))


if __name__ == "__main__":
    sys.exit(main())
