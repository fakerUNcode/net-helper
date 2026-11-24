from __future__ import annotations

from typing import Any

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QKeySequenceEdit,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
)

from rag.config import resolve_project_path
from rag.downloader import (
    check_offline_readiness,
    ensure_offline_embedding,
    ensure_offline_gguf,
    ensure_offline_mathjax,
)
from ui.hotkey_manager import pynput_to_qt_sequence, qt_sequence_to_pynput
from ui.theme import (
    BG_COLOR,
    BG_INPUT,
    BG_INPUT_FOCUS,
    BG_MUTED,
    BORDER_COLOR,
    BORDER_STRONG,
    BUTTON_TEXT_ON_ACCENT,
    DOWNLOAD_BTN_BG,
    DOWNLOAD_BTN_HOVER,
    LINK_COLOR,
    QT_SERIF_FONT_FAMILY,
    TEXT_COLOR,
    TEXT_MUTED,
    TEXT_SECONDARY,
    accent_button_qss,
    secondary_button_qss,
)


class _OfflineDownloadWorker(QObject):
    progress = Signal(object, object, str)
    finished = Signal()
    failed = Signal(str)

    def __init__(self, profile_key: str, gguf_raw_path: str) -> None:
        super().__init__()
        self._profile_key = profile_key
        self._gguf_raw_path = gguf_raw_path

    def run(self) -> None:
        try:
            def _cb(downloaded: int, total: int, label: str) -> None:
                self.progress.emit(downloaded, total, label)

            ensure_offline_mathjax(progress_cb=_cb)
            ensure_offline_embedding(progress_cb=_cb)
            gguf_dest = resolve_project_path(self._gguf_raw_path)
            ensure_offline_gguf(self._profile_key, gguf_dest, progress_cb=_cb)
            self.finished.emit()
        except Exception as exc:
            self.failed.emit(str(exc))


class HotkeySetupDialog(QDialog):
    """Minimal startup setup dialog: Select Model (3b/7b) and Set Hotkey."""

    def __init__(
        self,
        initial_pynput_hotkey: str,
        llm_cfg: dict[str, Any] | None = None,
        show_model_selector: bool = True,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Setup")
        self.setFixedWidth(360)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)

        self._selected_pynput = initial_pynput_hotkey
        self._llm_cfg = llm_cfg or {}
        self._profiles: dict[str, dict[str, Any]] = dict(self._llm_cfg.get("profiles") or {})
        self._selected_profile = str(self._llm_cfg.get("model_profile", "3b"))
        self._custom_model_paths: dict[str, str] = {}
        self._profile_radios: dict[str, QRadioButton] = {}
        self._dl_thread: QThread | None = None
        self._dl_worker: _OfflineDownloadWorker | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        if show_model_selector and self._profiles:
            model_header = QHBoxLayout()
            model_header.setSpacing(8)

            model_title = QLabel("Select Model")
            model_title.setStyleSheet(
                f"font-size: 14px; font-weight: 600; color: {TEXT_COLOR}; font-family: {QT_SERIF_FONT_FAMILY};"
            )
            model_header.addWidget(model_title)
            model_header.addStretch(1)

            self.download_btn = QPushButton("Download")
            self.download_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.download_btn.setStyleSheet(
                f"""
                QPushButton {{
                    background: {DOWNLOAD_BTN_BG};
                    color: {BUTTON_TEXT_ON_ACCENT};
                    border: none;
                    border-radius: 6px;
                    padding: 3px 10px;
                    font-size: 11px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background: {DOWNLOAD_BTN_HOVER};
                }}
                QPushButton:disabled {{
                    background: {BORDER_COLOR};
                    color: {TEXT_MUTED};
                }}
                """
            )
            self.download_btn.clicked.connect(self._start_offline_download)
            model_header.addWidget(self.download_btn)
            layout.addLayout(model_header)

            self._btn_group = QButtonGroup(self)
            for key in ("3b", "7b"):
                if key not in self._profiles:
                    continue
                prof = self._profiles[key]
                raw_path = str(prof.get("model_path", ""))
                self._custom_model_paths[key] = raw_path

                row = QHBoxLayout()
                row.setSpacing(8)
                radio = QRadioButton(key)
                radio.setStyleSheet(
                    f"""
                    QRadioButton {{
                        font-size: 13px;
                        color: {TEXT_COLOR};
                        spacing: 8px;
                    }}
                    QRadioButton::indicator {{
                        width: 14px;
                        height: 14px;
                        border-radius: 8px;
                        border: 1.5px solid {BORDER_STRONG};
                        background: {BG_INPUT_FOCUS};
                    }}
                    QRadioButton::indicator:checked {{
                        background: {LINK_COLOR};
                        border: 1.5px solid {LINK_COLOR};
                    }}
                    """
                )
                if key == self._selected_profile:
                    radio.setChecked(True)
                radio.toggled.connect(lambda _checked, k=key: self._on_profile_toggled())
                self._btn_group.addButton(radio)
                self._profile_radios[key] = radio
                row.addWidget(radio, 1)

                browse_btn = QPushButton("Browse")
                browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                browse_btn.setStyleSheet(secondary_button_qss(border_radius=6, padding="3px 8px", font_size=11))
                browse_btn.clicked.connect(lambda _c=False, k=key: self._browse_gguf(k))
                row.addWidget(browse_btn)
                layout.addLayout(row)

            self.download_progress = QProgressBar()
            self.download_progress.setFixedHeight(5)
            self.download_progress.setTextVisible(False)
            self.download_progress.setStyleSheet(
                f"""
                QProgressBar {{
                    background: {BORDER_COLOR};
                    border: none;
                    border-radius: 2px;
                }}
                QProgressBar::chunk {{
                    background: {LINK_COLOR};
                    border-radius: 2px;
                }}
                """
            )
            self.download_progress.hide()
            layout.addWidget(self.download_progress)

            self.download_detail_label = QLabel()
            self.download_detail_label.setStyleSheet(f"font-size: 11px; color: {LINK_COLOR};")
            self.download_detail_label.hide()
            layout.addWidget(self.download_detail_label)

            self._refresh_offline_summary()

        title = QLabel("Set Hotkey")
        title.setStyleSheet(
            f"font-size: 14px; font-weight: 600; color: {TEXT_COLOR}; margin-top: 2px; font-family: {QT_SERIF_FONT_FAMILY};"
        )
        layout.addWidget(title)

        self.key_edit = QKeySequenceEdit(QKeySequence(pynput_to_qt_sequence(initial_pynput_hotkey)))
        self.key_edit.setStyleSheet(
            f"""
            QKeySequenceEdit {{
                background: {BG_INPUT};
                border: 1px solid {BORDER_COLOR};
                border-radius: 8px;
                padding: 7px 10px;
                color: {TEXT_COLOR};
                font-size: 13px;
            }}
            QKeySequenceEdit:focus {{
                border: 1px solid {LINK_COLOR};
                background: {BG_INPUT_FOCUS};
            }}
            """
        )
        layout.addWidget(self.key_edit)

        preset_row = QHBoxLayout()
        preset_row.setSpacing(6)
        for label, pynput_val in [
            ("Ctrl+Shift+H", "<ctrl>+<shift>+h"),
            ("Alt+Space", "<alt>+<space>"),
            ("Ctrl+Alt+A", "<ctrl>+<alt>+a"),
        ]:
            btn = QPushButton(label)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(secondary_button_qss(border_radius=6, padding="3px 8px", font_size=11))
            btn.clicked.connect(
                lambda _checked=False, p=pynput_val: self.key_edit.setKeySequence(
                    QKeySequence(pynput_to_qt_sequence(p))
                )
            )
            preset_row.addWidget(btn)
        preset_row.addStretch(1)
        layout.addLayout(preset_row)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)

        cancel_btn = QPushButton("Cancel" if not show_model_selector else "Quit")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet(
            f"""
            QPushButton {{
                background: transparent;
                color: {TEXT_SECONDARY};
                border: 1px solid {BORDER_COLOR};
                border-radius: 8px;
                padding: 6px 14px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background: {BG_MUTED};
                color: {TEXT_COLOR};
                border-color: {BORDER_STRONG};
            }}
            """
        )
        cancel_btn.clicked.connect(self.reject)

        self.confirm_btn = QPushButton("Save" if not show_model_selector else "Start")
        self.confirm_btn.setDefault(True)
        self.confirm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.confirm_btn.setStyleSheet(accent_button_qss(border_radius=8, padding="6px 18px", font_size=12))
        self.confirm_btn.clicked.connect(self._on_confirm)

        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(self.confirm_btn)
        layout.addLayout(btn_row)

        self.setStyleSheet(f"QDialog {{ background-color: {BG_COLOR}; color: {TEXT_COLOR}; }}")

    def _active_profile_key(self) -> str:
        for key, radio in self._profile_radios.items():
            if radio.isChecked():
                return key
        return self._selected_profile

    def _on_profile_toggled(self) -> None:
        self._selected_profile = self._active_profile_key()
        self._refresh_offline_summary()

    def _refresh_offline_summary(self) -> None:
        if not hasattr(self, "download_btn"):
            return
        key = self._active_profile_key()
        raw_path = self._custom_model_paths.get(key, "")
        status = check_offline_readiness(resolve_project_path(raw_path))
        if status["all_ready"]:
            self.download_btn.setText("Ready")
            self.download_btn.setEnabled(False)
        else:
            self.download_btn.setText("Download")
            self.download_btn.setEnabled(True)

    def _start_offline_download(self) -> None:
        key = self._active_profile_key()
        raw_path = self._custom_model_paths.get(key, "")
        self.download_btn.setEnabled(False)
        self.confirm_btn.setEnabled(False)
        self.download_progress.setRange(0, 0)
        self.download_progress.show()
        self.download_detail_label.setText("...")
        self.download_detail_label.show()

        self._dl_thread = QThread(self)
        self._dl_worker = _OfflineDownloadWorker(key, raw_path)
        self._dl_worker.moveToThread(self._dl_thread)
        self._dl_thread.started.connect(self._dl_worker.run)
        self._dl_worker.progress.connect(self._on_download_progress)
        self._dl_worker.finished.connect(self._on_download_finished)
        self._dl_worker.failed.connect(self._on_download_failed)
        self._dl_worker.finished.connect(self._dl_thread.quit)
        self._dl_worker.failed.connect(self._dl_thread.quit)
        self._dl_thread.start()

    def _on_download_progress(self, downloaded: int, total: int, label: str) -> None:
        if total > 0:
            self.download_progress.setRange(0, 100)
            pct = min(100, int(downloaded * 100 / total))
            self.download_progress.setValue(pct)
            dl_mb = downloaded / (1024 * 1024)
            tot_mb = total / (1024 * 1024)
            self.download_detail_label.setText(f"{label} {dl_mb:.0f}/{tot_mb:.0f} MB ({pct}%)")
        else:
            self.download_progress.setRange(0, 0)
            self.download_detail_label.setText(label)

    def _on_download_finished(self) -> None:
        self.download_progress.hide()
        self.download_detail_label.hide()
        self.confirm_btn.setEnabled(True)
        self._refresh_offline_summary()

    def _on_download_failed(self, err: str) -> None:
        self.download_progress.hide()
        self.download_detail_label.hide()
        self.confirm_btn.setEnabled(True)
        self.download_btn.setEnabled(True)
        QMessageBox.warning(self, "Error", err)

    def _browse_gguf(self, key: str) -> None:
        models_dir = resolve_project_path("./models")
        models_dir.mkdir(parents=True, exist_ok=True)
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            f"{key} GGUF",
            str(models_dir),
            "GGUF (*.gguf);;All (*)",
        )
        if file_path:
            self._custom_model_paths[key] = file_path
            if key in self._profile_radios:
                self._profile_radios[key].setChecked(True)
            self._refresh_offline_summary()

    def _on_confirm(self) -> None:
        seq_str = self.key_edit.keySequence().toString(QKeySequence.SequenceFormat.PortableText)
        if seq_str:
            first_seq = seq_str.split(",")[0].strip()
            self._selected_pynput = qt_sequence_to_pynput(first_seq)
        self._selected_profile = self._active_profile_key()
        self.accept()

    def selected_hotkey(self) -> str:
        return self._selected_pynput

    def selected_profile(self) -> str:
        return self._selected_profile

    def selected_model_path(self) -> str:
        return self._custom_model_paths.get(self._selected_profile, "")
