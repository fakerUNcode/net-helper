from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from rag.config import load_config, save_config
from rag.llm import LocalLLMClient
from rag.retriever import VectorRetriever
from ui.assistant_window import FloatingAssistantWindow
from ui.hotkey_dialog import HotkeySetupDialog
from ui.hotkey_manager import GlobalHotkeyManager


def main() -> int:
    parser = argparse.ArgumentParser(description="最小完整答案弹窗助手")
    parser.add_argument("--config", type=Path, default=None, help="配置文件路径 (默认 ./config.yaml)")
    parser.add_argument(
        "--model",
        choices=["3b", "7b"],
        default=None,
        help="指定启动的本地 GGUF 模型版本 (3b: Qwen2.5-3B-Instruct, 7b: Qwen2.5-7B-Instruct)",
    )
    parser.add_argument(
        "--ingest-only",
        action="store_true",
        help="仅执行私有资料库入库，不启动桌面窗口",
    )
    parser.add_argument(
        "--skip-hotkey-setup",
        action="store_true",
        help="跳过启动前的快捷键与模型设置弹窗，直接使用 config.yaml 中的配置",
    )
    args = parser.parse_args()

    if args.ingest_only:
        from ingest import ingest

        ingest(config_path=args.config, rebuild=True)
        return 0

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    config = load_config(args.config)
    if args.model:
        config.setdefault("llm", {})["model_profile"] = args.model

    current_hotkey = str(config.get("app", {}).get("hotkey", "<ctrl>+<shift>+h"))

    if not args.skip_hotkey_setup:
        dialog = HotkeySetupDialog(current_hotkey, llm_cfg=config.get("llm", {}))
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return 0
        current_hotkey = dialog.selected_hotkey()
        config.setdefault("app", {})["hotkey"] = current_hotkey

        selected_profile = dialog.selected_profile()
        selected_path = dialog.selected_model_path()
        llm_cfg = config.setdefault("llm", {})
        llm_cfg["model_profile"] = selected_profile
        if selected_path:
            llm_cfg.setdefault("profiles", {}).setdefault(selected_profile, {})["model_path"] = selected_path
            llm_cfg["llama_cpp_model_path"] = selected_path

        save_config(config, args.config)

    retriever = VectorRetriever(config)
    if retriever.count() == 0:
        reply = QMessageBox.question(
            None,
            "知识库尚未入库",
            "当前向量库为空。\n是否立即扫描 ./docs 目录并构建向量索引？\n（首次运行将加载本地嵌入模型，可能需要数秒至数十秒）",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if reply == QMessageBox.StandardButton.Yes:
            from ingest import ingest

            ingest(config_path=args.config, rebuild=True)
            retriever = VectorRetriever(config)

    llm_client = LocalLLMClient(config["llm"])

    hotkey_manager = GlobalHotkeyManager()
    ok, err_msg = hotkey_manager.start(current_hotkey)
    hotkey_warning = "" if ok else err_msg

    window = FloatingAssistantWindow(
        config=config,
        retriever=retriever,
        llm_client=llm_client,
        hotkey_warning=hotkey_warning,
    )

    hotkey_manager.triggered.connect(window.toggle_visibility)

    def _rebind_hotkey() -> None:
        nonlocal current_hotkey
        dlg = HotkeySetupDialog(current_hotkey, show_model_selector=False)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_hotkey = dlg.selected_hotkey()
            ok_rebind, err_rebind = hotkey_manager.start(new_hotkey)
            if ok_rebind:
                current_hotkey = new_hotkey
                config.setdefault("app", {})["hotkey"] = current_hotkey
                save_config(config, args.config)
                window.update_hotkey_label(current_hotkey)
            else:
                QMessageBox.warning(window, "快捷键注册失败", err_rebind)

    window.rebind_hotkey_requested.connect(_rebind_hotkey)
    app.aboutToQuit.connect(hotkey_manager.stop)

    window.show()
    window.raise_()
    window.activateWindow()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())