from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QKeySequenceEdit,
    QLabel,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
)

from rag.config import resolve_project_path
from ui.hotkey_manager import pynput_to_qt_sequence, qt_sequence_to_pynput


class HotkeySetupDialog(QDialog):
    """每次启动前弹出：选择 Qwen2.5-3B / 7B GGUF 模型版本，并自定义全局一键隐藏/显示快捷键。"""

    def __init__(
        self,
        initial_pynput_hotkey: str,
        llm_cfg: dict[str, Any] | None = None,
        show_model_selector: bool = True,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("启动设置 - 模型版本与全局快捷键")
        self.setFixedWidth(460)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)

        self._selected_pynput = initial_pynput_hotkey
        self._llm_cfg = llm_cfg or {}
        self._profiles: dict[str, dict[str, Any]] = dict(self._llm_cfg.get("profiles") or {})
        self._selected_profile = str(self._llm_cfg.get("model_profile", "3b"))
        self._custom_model_paths: dict[str, str] = {}
        self._profile_radios: dict[str, QRadioButton] = {}
        self._profile_status_labels: dict[str, QLabel] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 18)
        layout.setSpacing(12)

        if show_model_selector and self._profiles:
            model_title = QLabel("选择本地 GGUF 模型版本（llama.cpp）")
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

        title = QLabel("设置「一键隐藏 / 显示」全局快捷键")
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

        confirm_btn = QPushButton("确认并启动")
        confirm_btn.setDefault(True)
        confirm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        confirm_btn.setStyleSheet(
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
        confirm_btn.clicked.connect(self._on_confirm)

        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(confirm_btn)
        layout.addLayout(btn_row)

        self.setStyleSheet("QDialog { background-color: #16181f; }")

    def _refresh_model_status(self, key: str) -> None:
        raw_path = self._custom_model_paths.get(key, "")
        resolved = resolve_project_path(raw_path) if raw_path else None
        lbl = self._profile_status_labels[key]
        if resolved and resolved.exists():
            size_gb = resolved.stat().st_size / (1024**3)
            lbl.setText(f"✓ 已就绪: {raw_path} ({size_gb:.2f} GB)")
            lbl.setStyleSheet("font-size: 11px; color: #34d399; padding-left: 20px;")
        else:
            lbl.setText(f"○ 未检测到文件: {raw_path}（请放入 ./models/ 或点击右侧选择）")
            lbl.setStyleSheet("font-size: 11px; color: #fbbf24; padding-left: 20px;")

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

    def _on_confirm(self) -> None:
        seq_str = self.key_edit.keySequence().toString(QKeySequence.SequenceFormat.PortableText)
        if seq_str:
            first_seq = seq_str.split(",")[0].strip()
            self._selected_pynput = qt_sequence_to_pynput(first_seq)
        for key, radio in self._profile_radios.items():
            if radio.isChecked():
                self._selected_profile = key
                break
        self.accept()

    def selected_hotkey(self) -> str:
        return self._selected_pynput

    def selected_profile(self) -> str:
        return self._selected_profile

    def selected_model_path(self) -> str:
        return self._custom_model_paths.get(self._selected_profile, "")