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
    """每次启动前弹出：选择 Qwen2.5-3B / 7B GGUF 版本、一键补全离线组件并设置全局快捷键。"""

    def __init__(
        self,
        initial_pynput_hotkey: str,
        llm_cfg: dict[str, Any] | None = None,
        show_model_selector: bool = True,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("启动设置 - 模型版本、离线组件与快捷键")
        self.setFixedWidth(480)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)

        self._selected_pynput = initial_pynput_hotkey
        self._llm_cfg = llm_cfg or {}
        self._profiles: dict[str, dict[str, Any]] = dict(self._llm_cfg.get("profiles") or {})
        self._selected_profile = str(self._llm_cfg.get("model_profile", "3b"))
        self._custom_model_paths: dict[str, str] = {}
        self._profile_radios: dict[str, QRadioButton] = {}
        self._profile_status_labels: dict[str, QLabel] = {}
        self._dl_thread: QThread | None = None
        self._dl_worker: _OfflineDownloadWorker | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 18)
        layout.setSpacing(10)

        if show_model_selector and self._profiles:
            model_title = QLabel("1. 选择本地模型版本（下载后可永久断网运行）")
            model_title.setStyleSheet("font-size: 15px; font-weight: 600; color: #f9fafb;")
            layout.addWidget(model_title)

            self._btn_group = QButtonGroup(self)
            for key in ("3b", "7b"):
                if key not in self._profiles:
                    continue
                prof = self._profiles[key]
                label_text = str(prof.get("label", f"Qwen2.5-{key.upper()}-Instruct"))
                raw_path = str(prof.get("model_path", ""))
                self._custom_model_paths[key] = raw_path

                row = QHBoxLayout()
                row.setSpacing(8)
                radio = QRadioButton(label_text)
                radio.setStyleSheet("font-size: 13px; color: #e5e7eb;")
                if key == self._selected_profile:
                    radio.setChecked(True)
                radio.toggled.connect(lambda _checked, k=key: self._on_profile_toggled())
                self._btn_group.addButton(radio)
                self._profile_radios[key] = radio
                row.addWidget(radio, 1)

                browse_btn = QPushButton("选择 GGUF")
                browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                browse_btn.setStyleSheet(
                    """
                    QPushButton {
                        background: rgba(255, 255, 255, 0.08);
                        color: #d1d5db;
                        border: 1px solid rgba(255, 255, 255, 0.14);
                        border-radius: 6px;
                        padding: 3px 8px;
                        font-size: 11px;
                    }
                    QPushButton:hover {
                        background: rgba(255, 255, 255, 0.16);
                    }
                    """
                )
                browse_btn.clicked.connect(lambda _c=False, k=key: self._browse_gguf(k))
                row.addWidget(browse_btn)
                layout.addLayout(row)

                status_lbl = QLabel()
                status_lbl.setStyleSheet("font-size: 11px; padding-left: 20px;")
                self._profile_status_labels[key] = status_lbl
                layout.addWidget(status_lbl)
                self._refresh_model_status(key)

            # 离线组件状态与一键下载区
            offline_row = QHBoxLayout()
            offline_row.setSpacing(8)
            self.offline_status_label = QLabel()
            self.offline_status_label.setWordWrap(True)
            self.offline_status_label.setStyleSheet("font-size: 11px; color: #9ca3af;")
            offline_row.addWidget(self.offline_status_label, 1)

            self.download_btn = QPushButton("一键下载离线组件")
            self.download_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.download_btn.setStyleSheet(
                """
                QPushButton {
                    background: #059669;
                    color: #ffffff;
                    border: none;
                    border-radius: 6px;
                    padding: 5px 10px;
                    font-size: 12px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background: #10b981;
                }
                QPushButton:disabled {
                    background: rgba(75, 85, 99, 140);
                    color: rgba(209, 213, 219, 140);
                }
                """
            )
            self.download_btn.clicked.connect(self._start_offline_download)
            offline_row.addWidget(self.download_btn)
            layout.addLayout(offline_row)

            self.download_progress = QProgressBar()
            self.download_progress.setFixedHeight(6)
            self.download_progress.setTextVisible(False)
            self.download_progress.setStyleSheet(
                """
                QProgressBar {
                    background: rgba(255, 255, 255, 18);
                    border: none;
                    border-radius: 3px;
                }
                QProgressBar::chunk {
                    background: #10b981;
                    border-radius: 3px;
                }
                """
            )
            self.download_progress.hide()
            layout.addWidget(self.download_progress)

            self.download_detail_label = QLabel()
            self.download_detail_label.setStyleSheet("font-size: 11px; color: #93c5fd;")
            self.download_detail_label.hide()
            layout.addWidget(self.download_detail_label)

            self._refresh_offline_summary()

        title = QLabel("2. 设置「一键隐藏 / 显示」全局快捷键")
        title.setStyleSheet("font-size: 15px; font-weight: 600; color: #f9fafb; margin-top: 4px;")
        layout.addWidget(title)

        desc = QLabel(
            "点击下方输入框并直接按下组合键（例如 Ctrl+Shift+H 或 Alt+Space）。\n"
            "启动后在任何界面按下该快捷键即可隐藏或显示左下角助手。"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 12px; color: #9ca3af; line-height: 1.4;")
        layout.addWidget(desc)

        self.key_edit = QKeySequenceEdit(QKeySequence(pynput_to_qt_sequence(initial_pynput_hotkey)))
        self.key_edit.setStyleSheet(
            """
            QKeySequenceEdit {
                background: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.22);
                border-radius: 8px;
                padding: 8px 12px;
                color: #f9fafb;
                font-size: 14px;
            }
            QKeySequenceEdit:focus {
                border: 1px solid #60a5fa;
            }
            """
        )
        layout.addWidget(self.key_edit)

        preset_row = QHBoxLayout()
        preset_row.setSpacing(8)
        preset_label = QLabel("快捷预设:")
        preset_label.setStyleSheet("font-size: 12px; color: #9ca3af;")
        preset_row.addWidget(preset_label)

        for label, pynput_val in [
            ("Ctrl+Shift+H", "<ctrl>+<shift>+h"),
            ("Alt+Space", "<alt>+<space>"),
            ("Ctrl+Alt+A", "<ctrl>+<alt>+a"),
        ]:
            btn = QPushButton(label)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(
                """
                QPushButton {
                    background: rgba(255, 255, 255, 0.08);
                    color: #d1d5db;
                    border: 1px solid rgba(255, 255, 255, 0.14);
                    border-radius: 6px;
                    padding: 4px 8px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background: rgba(255, 255, 255, 0.16);
                }
                """
            )
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

        cancel_btn = QPushButton("退出")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet(
            """
            QPushButton {
                background: transparent;
                color: #9ca3af;
                border: 1px solid rgba(255, 255, 255, 0.18);
                border-radius: 8px;
                padding: 7px 14px;
                font-size: 13px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.08);
                color: #f3f4f6;
            }
            """
        )
        cancel_btn.clicked.connect(self.reject)

        self.confirm_btn = QPushButton("确认并启动")
        self.confirm_btn.setDefault(True)
        self.confirm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.confirm_btn.setStyleSheet(
            """
            QPushButton {
                background: #2563eb;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 7px 18px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #3b82f6;
            }
            """
        )
        self.confirm_btn.clicked.connect(self._on_confirm)

        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(self.confirm_btn)
        layout.addLayout(btn_row)

        self.setStyleSheet("QDialog { background-color: #16181f; }")

    def _active_profile_key(self) -> str:
        for key, radio in self._profile_radios.items():
            if radio.isChecked():
                return key
        return self._selected_profile

    def _on_profile_toggled(self) -> None:
        self._selected_profile = self._active_profile_key()
        self._refresh_offline_summary()

    def _refresh_model_status(self, key: str) -> None:
        raw_path = self._custom_model_paths.get(key, "")
        resolved = resolve_project_path(raw_path) if raw_path else None
        lbl = self._profile_status_labels[key]
        if resolved and resolved.exists():
            size_gb = resolved.stat().st_size / (1024**3)
            lbl.setText(f"✓ 已就绪: {raw_path} ({size_gb:.2f} GB)")
            lbl.setStyleSheet("font-size: 11px; color: #34d399; padding-left: 20px;")
        else:
            lbl.setText(f"○ 未下载: {raw_path}（可点击下方「一键下载离线组件」）")
            lbl.setStyleSheet("font-size: 11px; color: #fbbf24; padding-left: 20px;")

    def _refresh_offline_summary(self) -> None:
        if not hasattr(self, "offline_status_label"):
            return
        key = self._active_profile_key()
        raw_path = self._custom_model_paths.get(key, "")
        status = check_offline_readiness(resolve_project_path(raw_path))
        if status["all_ready"]:
            self.offline_status_label.setText("✓ 全部离线组件已就绪（支持完全断网运行）")
            self.offline_status_label.setStyleSheet("font-size: 11px; color: #34d399;")
            self.download_btn.setText("离线已就绪")
            self.download_btn.setEnabled(False)
        else:
            missing = []
            if not status["gguf"]:
                missing.append(f"{key.upper()} GGUF")
            if not status["embedding"]:
                missing.append("嵌入模型")
            if not status["mathjax"]:
                missing.append("MathJax")
            self.offline_status_label.setText(f"待补全离线组件: {', '.join(missing)}")
            self.offline_status_label.setStyleSheet("font-size: 11px; color: #fbbf24;")
            self.download_btn.setText("一键下载离线组件")
            self.download_btn.setEnabled(True)

    def _start_offline_download(self) -> None:
        key = self._active_profile_key()
        raw_path = self._custom_model_paths.get(key, "")
        self.download_btn.setEnabled(False)
        self.confirm_btn.setEnabled(False)
        self.download_progress.setRange(0, 0)
        self.download_progress.show()
        self.download_detail_label.setText("正在准备下载...")
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
            self.download_detail_label.setText(f"{label}: {dl_mb:.1f} MB / {tot_mb:.1f} MB ({pct}%)")
        else:
            self.download_progress.setRange(0, 0)
            self.download_detail_label.setText(label)

    def _on_download_finished(self) -> None:
        self.download_progress.hide()
        self.download_detail_label.hide()
        self.confirm_btn.setEnabled(True)
        for key in self._profile_radios:
            self._refresh_model_status(key)
        self._refresh_offline_summary()

    def _on_download_failed(self, err: str) -> None:
        self.download_progress.hide()
        self.download_detail_label.hide()
        self.confirm_btn.setEnabled(True)
        self.download_btn.setEnabled(True)
        QMessageBox.warning(self, "离线组件下载失败", err)

    def _browse_gguf(self, key: str) -> None:
        models_dir = resolve_project_path("./models")
        models_dir.mkdir(parents=True, exist_ok=True)
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            f"选择 {key.upper()} GGUF 模型文件",
            str(models_dir),
            "GGUF 模型 (*.gguf);;所有文件 (*)",
        )
        if file_path:
            self._custom_model_paths[key] = file_path
            if key in self._profile_radios:
                self._profile_radios[key].setChecked(True)
            self._refresh_model_status(key)
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