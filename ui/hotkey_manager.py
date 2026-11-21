from __future__ import annotations

import sys
from PySide6.QtCore import QObject, Signal


def qt_sequence_to_pynput(seq_str: str) -> str:
    """将 Qt QKeySequence 字符串 (如 'Ctrl+Shift+H') 转换为 pynput GlobalHotKeys 格式。"""
    if not seq_str:
        return "<ctrl>+<shift>+h"

    parts = [p.strip() for p in seq_str.split("+") if p.strip()]
    is_mac = sys.platform == "darwin"

    mapped: list[str] = []
    special_keys = {
        "space": "<space>",
        "tab": "<tab>",
        "return": "<enter>",
        "enter": "<enter>",
        "esc": "<esc>",
        "escape": "<esc>",
        "backspace": "<backspace>",
        "delete": "<delete>",
        "up": "<up>",
        "down": "<down>",
        "left": "<left>",
        "right": "<right>",
        "home": "<home>",
        "end": "<end>",
        "pgup": "<page_up>",
        "pgdown": "<page_down>",
    }

    for part in parts:
        low = part.lower()
        if low == "ctrl":
            mapped.append("<cmd>" if is_mac else "<ctrl>")
        elif low == "meta":
            mapped.append("<ctrl>" if is_mac else "<cmd>")
        elif low == "alt":
            mapped.append("<alt>")
        elif low == "shift":
            mapped.append("<shift>")
        elif low in special_keys:
            mapped.append(special_keys[low])
        elif low.startswith("f") and low[1:].isdigit():
            mapped.append(f"<{low}>")
        else:
            mapped.append(low)

    return "+".join(mapped)


def pynput_to_qt_sequence(pynput_str: str) -> str:
    """将 pynput 格式 (如 '<ctrl>+<shift>+h') 转换为 Qt QKeySequence 字符串。"""
    if not pynput_str:
        return "Ctrl+Shift+H"

    is_mac = sys.platform == "darwin"
    parts = [p.strip() for p in pynput_str.split("+") if p.strip()]
    mapped: list[str] = []

    reverse_special = {
        "<space>": "Space",
        "<tab>": "Tab",
        "<enter>": "Return",
        "<esc>": "Esc",
        "<backspace>": "Backspace",
        "<delete>": "Delete",
        "<up>": "Up",
        "<down>": "Down",
        "<left>": "Left",
        "<right>": "Right",
        "<home>": "Home",
        "<end>": "End",
        "<page_up>": "PgUp",
        "<page_down>": "PgDown",
    }

    for part in parts:
        low = part.lower()
        if low == "<ctrl>":
            mapped.append("Meta" if is_mac else "Ctrl")
        elif low == "<cmd>":
            mapped.append("Ctrl" if is_mac else "Meta")
        elif low == "<alt>":
            mapped.append("Alt")
        elif low == "<shift>":
            mapped.append("Shift")
        elif low in reverse_special:
            mapped.append(reverse_special[low])
        elif low.startswith("<") and low.endswith(">"):
            mapped.append(low[1:-1].upper())
        else:
            mapped.append(part.upper() if len(part) == 1 else part.capitalize())

    return "+".join(mapped)


def format_hotkey_label(pynput_str: str) -> str:
    """格式化用于 UI 展示的快捷键文本。"""
    tokens = [t.strip().strip("<>").capitalize() for t in pynput_str.split("+") if t.strip()]
    return "+".join(tokens)


class GlobalHotkeyManager(QObject):
    """跨平台全局快捷键管理器，通过 Qt Signal 线程安全地切换窗口显隐。"""

    triggered = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._listener = None
        self._current_hotkey = ""

    def start(self, pynput_hotkey: str) -> tuple[bool, str]:
        self.stop()
        self._current_hotkey = pynput_hotkey
        try:
            from pynput import keyboard

            def _on_activate() -> None:
                self.triggered.emit()

            self._listener = keyboard.GlobalHotKeys({pynput_hotkey: _on_activate})
            self._listener.start()
            return True, ""
        except Exception as exc:
            self._listener = None
            return False, f"全局快捷键注册失败 ({pynput_hotkey}): {exc}"

    def stop(self) -> None:
        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None
