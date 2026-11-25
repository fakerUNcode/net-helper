from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QThread, QTimer, Signal
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox, QProgressDialog

from rag.config import load_config, save_config
from rag.llm import LocalLLMClient
from rag.manifest import check_index_status
from rag.retriever import VectorRetriever
from ui.assistant_window import FloatingAssistantWindow
from ui.hotkey_dialog import HotkeySetupDialog
from ui.hotkey_manager import GlobalHotkeyManager
from ui.theme import message_box_qss, set_active_theme


class _StartupIngestWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, config_path: Path | None) -> None:
        super().__init__()
        self._config_path = config_path

    def run(self) -> None:
        try:
            from ingest import ingest

            result = ingest(config_path=self._config_path, rebuild=True)
            self.finished.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))


def _run_ingest_with_dialog(config_path: Path | None, label_text: str = "Building vector index from ./docs...") -> bool:
    progress = QProgressDialog(label_text, "", 0, 0)
    progress.setWindowTitle("NetHelper")
    progress.setCancelButton(None)
    progress.setWindowModality(Qt.WindowModality.ApplicationModal)
    progress.setWindowFlags(progress.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
    progress.setMinimumDuration(0)
    progress.setRange(0, 0)

    thread = QThread()
    worker = _StartupIngestWorker(config_path)
    worker.moveToThread(thread)

    outcome: dict[str, object] = {"ok": False, "error": ""}

    def _on_done(res: object) -> None:
        outcome["ok"] = True
        outcome["result"] = res
        progress.close()

    def _on_fail(err: str) -> None:
        outcome["ok"] = False
        outcome["error"] = err
        progress.close()

    thread.started.connect(worker.run)
    worker.finished.connect(_on_done)
    worker.failed.connect(_on_fail)
    worker.finished.connect(thread.quit)
    worker.failed.connect(thread.quit)
    thread.finished.connect(worker.deleteLater)
    thread.finished.connect(thread.deleteLater)

    QTimer.singleShot(0, thread.start)
    progress.exec()
    thread.wait()

    if not outcome["ok"]:
        QMessageBox.critical(None, "Index Build Failed", str(outcome["error"]))
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="NetHelper")
    parser.add_argument("--config", type=Path, default=None, help="Config path")
    parser.add_argument(
        "--model",
        choices=["3b", "7b", "8b", "14b"],
        default=None,
        help="Model (3b, 7b, 8b, or 14b)",
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

    config = load_config(args.config)
    if args.model:
        config.setdefault("llm", {})["model_profile"] = args.model

    current_hotkey = str(config.get("app", {}).get("hotkey", "<ctrl>+<shift>+h"))
    current_theme = set_active_theme(str(config.get("app", {}).get("theme", "sepia"))).key
    app.setStyleSheet(message_box_qss())

    index_status = check_index_status(config)
    should_rebuild_from_dialog = False

    if not args.skip_hotkey_setup:
        dialog = HotkeySetupDialog(
            current_hotkey,
            llm_cfg=config.get("llm", {}),
            initial_theme=current_theme,
            index_status=index_status,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return 0
        current_hotkey = dialog.selected_hotkey()
        config.setdefault("app", {})["hotkey"] = current_hotkey
        current_theme = set_active_theme(dialog.selected_theme()).key
        config.setdefault("app", {})["theme"] = current_theme
        app.setStyleSheet(message_box_qss())

        selected_profile = dialog.selected_profile()
        selected_path = dialog.selected_model_path()
        llm_cfg = config.setdefault("llm", {})
        llm_cfg["model_profile"] = selected_profile
        if selected_path:
            llm_cfg.setdefault("profiles", {}).setdefault(selected_profile, {})["model_path"] = selected_path
            llm_cfg["llama_cpp_model_path"] = selected_path

        should_rebuild_from_dialog = dialog.should_rebuild_index()
        save_config(config, args.config)

    if should_rebuild_from_dialog:
        _run_ingest_with_dialog(args.config, "Rebuilding vector index from ./docs...")

    retriever = VectorRetriever(config)
    existing_count = retriever.count()
    if existing_count == 0 or (args.skip_hotkey_setup and index_status.needs_rebuild):
        prompt_title = "Index Empty" if existing_count == 0 else "Documents Updated"
        prompt_body = (
            "Build index from ./docs?"
            if existing_count == 0
            else f"{index_status.reason}. Rebuild index from ./docs?"
        )
        reply = QMessageBox.question(
            None,
            prompt_title,
            prompt_body,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if reply == QMessageBox.StandardButton.Yes:
            if _run_ingest_with_dialog(args.config, "Rebuilding vector index from ./docs..."):
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
        config_path=args.config,
    )

    hotkey_manager.triggered.connect(window.toggle_visibility)

    def _rebind_hotkey() -> None:
        nonlocal current_hotkey, current_theme
        dlg = HotkeySetupDialog(
            current_hotkey,
            show_model_selector=False,
            initial_theme=current_theme,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_hotkey = dlg.selected_hotkey()
            new_theme = set_active_theme(dlg.selected_theme()).key
            theme_changed = new_theme != current_theme
            if theme_changed:
                current_theme = new_theme
                config.setdefault("app", {})["theme"] = current_theme
                app.setStyleSheet(message_box_qss())
                window.apply_theme(current_theme)
            ok_rebind, err_rebind = hotkey_manager.start(new_hotkey)
            if ok_rebind:
                current_hotkey = new_hotkey
                config.setdefault("app", {})["hotkey"] = current_hotkey
                save_config(config, args.config)
                window.update_hotkey_label(current_hotkey)
            else:
                if theme_changed:
                    save_config(config, args.config)
                QMessageBox.warning(window, "Hotkey Error", err_rebind)

    window.rebind_hotkey_requested.connect(_rebind_hotkey)
    app.aboutToQuit.connect(hotkey_manager.stop)

    window.show()
    window.raise_()
    window.activateWindow()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
