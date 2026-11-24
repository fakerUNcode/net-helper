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
from ui.theme import message_box_qss


def main() -> int:
    parser = argparse.ArgumentParser(description="NetHelper")
    parser.add_argument("--config", type=Path, default=None, help="Config path")
    parser.add_argument(
        "--model",
        choices=["3b", "7b"],
        default=None,
        help="Model (3b or 7b)",
    )
    parser.add_argument(
        "--ingest-only",
        action="store_true",
        help="Ingest only",
    )
    parser.add_argument(
        "--skip-hotkey-setup",
        action="store_true",
        help="Skip setup dialog",
    )
    args = parser.parse_args()

    if args.ingest_only:
        from ingest import ingest

        ingest(config_path=args.config, rebuild=True)
        return 0

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setStyleSheet(message_box_qss())

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
            "Index Empty",
            "Build index from ./docs?",
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
                QMessageBox.warning(window, "Hotkey Error", err_rebind)

    window.rebind_hotkey_requested.connect(_rebind_hotkey)
    app.aboutToQuit.connect(hotkey_manager.stop)

    window.show()
    window.raise_()
    window.activateWindow()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())