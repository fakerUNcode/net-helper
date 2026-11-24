from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"
APP_NAME = "NetHelper"


def _ensure_pyinstaller() -> None:
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("[1/4] 正在安装 PyInstaller...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller>=6.0.0"], check=True)


def _collect_pyinstaller_args(console: bool = False) -> list[str]:
    args = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onedir",
        "--name",
        APP_NAME,
    ]
    if not console:
        args.append("--windowed")

    hidden_imports = [
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtWebEngineCore",
        "chromadb",
        "chromadb.telemetry.product.posthog",
        "sentence_transformers",
        "tiktoken_ext",
        "tiktoken_ext.openai_public",
        "pynput.keyboard._darwin" if sys.platform == "darwin" else "pynput.keyboard._win32" if os.name == "nt" else "pynput.keyboard._xorg",
        "pynput.mouse._darwin" if sys.platform == "darwin" else "pynput.mouse._win32" if os.name == "nt" else "pynput.mouse._xorg",
        "pygments.styles.gruvbox",
        "markdown.extensions.fenced_code",
        "markdown.extensions.codehilite",
        "markdown.extensions.tables",
        "markdown.extensions.sane_lists",
        "markdown.extensions.nl2br",
        "llama_cpp",
        "fitz",
        "pypdf",
    ]
    for mod in hidden_imports:
        args.extend(["--hidden-import", mod])

    collect_all = ["chromadb", "llama_cpp"]
    for pkg in collect_all:
        args.extend(["--collect-all", pkg])

    args.append(str(PROJECT_ROOT / "main.py"))
    return args


def _prepare_bundle_files(target_dir: Path) -> None:
    print(f"[3/4] 正在写入分发目录配置与离线资源: {target_dir}")
    target_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(PROJECT_ROOT / "config.yaml", target_dir / "config.yaml")

    for sub in ("docs", "models", "vector_store"):
        sub_dir = target_dir / sub
        sub_dir.mkdir(parents=True, exist_ok=True)
        readme = PROJECT_ROOT / sub / "README.md"
        if readme.exists():
            shutil.copy2(readme, sub_dir / "README.md")

    try:
        from rag.downloader import ensure_offline_mathjax

        ensure_offline_mathjax()
    except Exception as exc:
        print(f"[提示] 预下载 MathJax 失败（首次运行可一键补全）: {exc}")

    assets_dir = PROJECT_ROOT / "assets"
    if assets_dir.exists():
        shutil.copytree(assets_dir, target_dir / "assets", dirs_exist_ok=True)


def _create_archive(target_dir: Path) -> list[Path]:
    sys_name = {"darwin": "macos", "win32": "windows", "linux": "linux"}.get(sys.platform, sys.platform)
    arch = platform.machine().lower()
    base_name = DIST_DIR / f"{APP_NAME}-{sys_name}-{arch}"
    fmt = "gztar" if sys.platform == "linux" else "zip"
    print(f"[4/4] 正在生成分发包 ({fmt})...")
    outputs: list[Path] = []
    archive_path = Path(shutil.make_archive(str(base_name), fmt, root_dir=DIST_DIR, base_dir=target_dir.name))
    outputs.append(archive_path)

    if sys.platform == "darwin" and shutil.which("hdiutil"):
        dmg_path = DIST_DIR / f"{APP_NAME}-{sys_name}-{arch}.dmg"
        if dmg_path.exists():
            dmg_path.unlink()
        try:
            subprocess.run(
                [
                    "hdiutil",
                    "create",
                    "-volname",
                    APP_NAME,
                    "-srcfolder",
                    str(target_dir),
                    "-ov",
                    "-format",
                    "UDZO",
                    str(dmg_path),
                ],
                check=True,
            )
            outputs.append(dmg_path)
        except Exception as exc:
            print(f"[提示] DMG 生成跳过: {exc}")

    if sys.platform == "win32":
        iscc = shutil.which("iscc") or shutil.which("ISCC.exe")
        if iscc:
            iss_file = BUILD_DIR / f"{APP_NAME}.iss"
            iss_file.parent.mkdir(parents=True, exist_ok=True)
            iss_content = f"""[Setup]
AppName={APP_NAME}
AppVersion=1.0.0
DefaultDirName={{autopf}}\\{APP_NAME}
DefaultGroupName={APP_NAME}
OutputDir={DIST_DIR}
OutputBaseFilename={APP_NAME}-{sys_name}-{arch}-Setup
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest

[Files]
Source: "{target_dir}\\*"; DestDir: "{{app}}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{{group}}\\{APP_NAME}"; Filename: "{{app}}\\{APP_NAME}.exe"
Name: "{{autodesktop}}\\{APP_NAME}"; Filename: "{{app}}\\{APP_NAME}.exe"

[Run]
Filename: "{{app}}\\{APP_NAME}.exe"; Description: "启动 {APP_NAME}"; Flags: nowait postinstall skipifsilent
"""
            iss_file.write_text(iss_content, encoding="utf-8")
            try:
                subprocess.run([iscc, str(iss_file)], check=True)
                setup_exe = DIST_DIR / f"{APP_NAME}-{sys_name}-{arch}-Setup.exe"
                if setup_exe.exists():
                    outputs.append(setup_exe)
            except Exception as exc:
                print(f"[提示] Inno Setup 安装包生成跳过: {exc}")

    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(description="将项目打包为可分发到 macOS / Windows / Linux 的独立程序。")
    parser.add_argument("--console", action="store_true", help="保留控制台窗口（便于排查日志）")
    parser.add_argument("--archive", action="store_true", help="打包后生成 .zip / .tar.gz 分发压缩包")
    args = parser.parse_args()

    _ensure_pyinstaller()
    print("[2/4] 正在执行 PyInstaller 打包...")
    subprocess.run(_collect_pyinstaller_args(console=args.console), cwd=str(PROJECT_ROOT), check=True)

    bundle_dir = DIST_DIR / APP_NAME
    if sys.platform == "darwin" and not args.console and (DIST_DIR / f"{APP_NAME}.app").exists():
        # macOS 下 --windowed 会生成 NetHelper.app；将配置与数据目录放在 dist/NetHelper_Dist/ 下以便用户直接放置模型与文档
        release_dir = DIST_DIR / f"{APP_NAME}-macOS"
        release_dir.mkdir(parents=True, exist_ok=True)
        app_dest = release_dir / f"{APP_NAME}.app"
        if app_dest.exists():
            shutil.rmtree(app_dest)
        shutil.move(str(DIST_DIR / f"{APP_NAME}.app"), str(app_dest))
        _prepare_bundle_files(release_dir)
        bundle_dir = release_dir
    else:
        _prepare_bundle_files(bundle_dir)

    if args.archive:
        archive_paths = _create_archive(bundle_dir)
        for p in archive_paths:
            print(f"打包完成: {p}")
    else:
        print(f"打包完成: {bundle_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
