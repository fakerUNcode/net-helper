from __future__ import annotations

import html
from typing import Any

from PySide6.QtCore import QEvent, QObject, QPoint, QRect, Qt, QThread, QUrl, Signal
from PySide6.QtGui import QAction, QColor, QGuiApplication
from PySide6.QtWebEngineCore import QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QSizePolicy,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from rag.config import PROJECT_ROOT
from rag.postprocess import postprocess_answer
from rag.prompt import build_messages
from ui.hotkey_manager import format_hotkey_label
from ui.renderer import render_answer_html
from ui.theme import (
    BG_CARD_RGBA,
    BG_INPUT,
    BG_INPUT_FOCUS,
    BG_MUTED,
    BORDER_CARD,
    BORDER_COLOR,
    LINK_COLOR,
    QT_SERIF_FONT_FAMILY,
    SELECTION_QT_BG,
    TEXT_COLOR,
    TEXT_MUTED,
    TEXT_SECONDARY,
    WARNING_TEXT,
    accent_button_qss,
    ghost_icon_button_qss,
    tray_menu_qss,
)


class _QueryWorker(QObject):
    """后台执行 RAG 检索 + 本地 LLM 缓冲生成 + 后处理，绝不向 UI 发送流式中间 token。"""

    finished = Signal(str)
    failed = Signal(str)

    def __init__(self, question: str, retriever: Any, llm_client: Any, top_k: int) -> None:
        super().__init__()
        self._question = question
        self._retriever = retriever
        self._llm_client = llm_client
        self._top_k = top_k

    def run(self) -> None:
        try:
            chunks = self._retriever.retrieve(self._question, top_k=self._top_k)
            messages = build_messages(self._question, chunks)
            raw_answer = self._llm_client.generate_complete(messages)
            final_answer = postprocess_answer(raw_answer)
            if not final_answer:
                final_answer = "No relevant information."
            self.finished.emit(final_answer)
        except Exception as exc:
            self.failed.emit(str(exc))


class FloatingAssistantWindow(QWidget):
    """左下角半透明悬浮助手：提问态仅显示输入框，生成结束后弹出完整答案窗口并支持 Restart。"""

    rebind_hotkey_requested = Signal()

    def __init__(
        self,
        config: dict[str, Any],
        retriever: Any,
        llm_client: Any,
        hotkey_warning: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.config = config
        self.retriever = retriever
        self.llm_client = llm_client
        self._hotkey_warning = hotkey_warning

        app_cfg = config.get("app", {})
        self._app_name = str(app_cfg.get("name", "NetHelper"))
        self._hotkey_label = format_hotkey_label(str(app_cfg.get("hotkey", "<ctrl>+<shift>+h")))
        self._opacity = max(0.2, min(1.0, float(app_cfg.get("window_opacity", 0.70))))
        self._input_width = int(app_cfg.get("input_width", 360))
        self._input_height = int(app_cfg.get("input_height", 60))
        self._window_width = self._input_width
        self._window_height = int(app_cfg.get("answer_max_height", 117))
        self._margin_x = int(app_cfg.get("margin_x", 24))
        self._margin_y = int(app_cfg.get("margin_y", 24))
        self._top_k = int(config.get("vector_store", {}).get("top_k", 3))

        self._resize_margin = 8
        self._drag_offset: QPoint | None = None
        self._resize_edges: tuple[bool, bool, bool, bool] | None = None
        self._resize_start_pos: QPoint | None = None
        self._resize_start_geo: QRect | None = None
        self._worker_thread: QThread | None = None
        self._worker: _QueryWorker | None = None
        self._is_generating = False
        self._in_answer_mode = False

        self._setup_window_flags()
        self._build_ui()
        self.setMinimumSize(260, 80)
        self.resize(self._window_width, self._window_height)
        self._setup_tray()
        app_inst = QGuiApplication.instance()
        if app_inst is not None:
            app_inst.applicationStateChanged.connect(self._on_app_state_changed)
        self._enter_input_mode()
        self._anchor_bottom_left()

    def _setup_window_flags(self) -> None:
        self.setWindowTitle(self._app_name)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowOpacity(self._opacity)
        self.setMouseTracking(True)

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.card = QFrame(self)
        self.card.setObjectName("FloatingCard")
        self.card.setMouseTracking(True)
        self.card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.card.setStyleSheet(
            f"""
            #FloatingCard {{
                background-color: {BG_CARD_RGBA};
                border: 1px solid {BORDER_CARD};
                border-radius: 12px;
            }}
            """
        )
        root_layout.addWidget(self.card, 1)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(8, 8, 8, 6)
        card_layout.setSpacing(6)

        # --- 1. 答案弹窗区域（默认隐藏，仅在生成结束后展示） ---
        self.answer_container = QWidget(self.card)
        self.answer_container.setMouseTracking(True)
        self.answer_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        answer_layout = QVBoxLayout(self.answer_container)
        answer_layout.setContentsMargins(0, 0, 0, 0)
        answer_layout.setSpacing(6)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(2, 0, 2, 0)
        header_row.setSpacing(8)

        self.title_label = QLabel(self._hotkey_label)
        self.title_label.setStyleSheet(f"font-size: 11px; color: {TEXT_SECONDARY};")
        header_row.addWidget(self.title_label)
        header_row.addStretch(1)

        self.restart_btn = QPushButton("↻")
        self.restart_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.restart_btn.setToolTip("Restart")
        self.restart_btn.setFixedSize(26, 26)
        self.restart_btn.setStyleSheet(accent_button_qss(border_radius=6, font_size=14))
        self.restart_btn.clicked.connect(self._on_restart_clicked)
        header_row.addWidget(self.restart_btn)

        self.hide_btn_answer = QPushButton("—")
        self.hide_btn_answer.setCursor(Qt.CursorShape.PointingHandCursor)
        self.hide_btn_answer.setToolTip("Hide")
        self.hide_btn_answer.setFixedSize(24, 24)
        self.hide_btn_answer.setStyleSheet(ghost_icon_button_qss(border_radius=6, font_size=12))
        self.hide_btn_answer.clicked.connect(self.hide)
        header_row.addWidget(self.hide_btn_answer)

        answer_layout.addLayout(header_row)

        self.web_view = QWebEngineView(self.answer_container)
        self.web_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.web_view.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.web_view.setStyleSheet("background: transparent;")
        self.web_view.page().setBackgroundColor(QColor(0, 0, 0, 0))
        web_settings = self.web_view.settings()
        web_settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        web_settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        answer_layout.addWidget(self.web_view, 1)

        card_layout.addWidget(self.answer_container, 1)

        # --- 2. 提问输入条（提问态仅显示此部分） ---
        self.input_container = QWidget(self.card)
        self.input_container.setMouseTracking(True)
        input_vlayout = QVBoxLayout(self.input_container)
        input_vlayout.setContentsMargins(0, 0, 0, 0)
        input_vlayout.setSpacing(6)

        input_row = QHBoxLayout()
        input_row.setContentsMargins(0, 0, 0, 0)
        input_row.setSpacing(8)

        self.input_edit = QLineEdit(self.input_container)
        self.input_edit.setPlaceholderText("")
        self.input_edit.setStyleSheet(
            f"""
            QLineEdit {{
                background: {BG_INPUT};
                border: 1px solid {BORDER_COLOR};
                border-radius: 8px;
                padding: 8px 12px;
                color: {TEXT_COLOR};
                selection-background-color: {SELECTION_QT_BG};
                selection-color: {TEXT_COLOR};
                font-family: {QT_SERIF_FONT_FAMILY};
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border: 1px solid {LINK_COLOR};
                background: {BG_INPUT_FOCUS};
            }}
            QLineEdit:disabled {{
                background: {BG_MUTED};
                color: {TEXT_MUTED};
            }}
            """
        )
        self.input_edit.returnPressed.connect(self._on_submit)
        input_row.addWidget(self.input_edit, 1)

        self.send_btn = QPushButton("➤")
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.setToolTip("Send")
        self.send_btn.setFixedSize(32, 32)
        self.send_btn.setStyleSheet(accent_button_qss(border_radius=8, font_size=13))
        self.send_btn.clicked.connect(self._on_submit)
        input_row.addWidget(self.send_btn)

        self.hide_btn_input = QPushButton("—")
        self.hide_btn_input.setCursor(Qt.CursorShape.PointingHandCursor)
        self.hide_btn_input.setToolTip("Hide")
        self.hide_btn_input.setFixedSize(28, 32)
        self.hide_btn_input.setStyleSheet(ghost_icon_button_qss(border_radius=8, font_size=12))
        self.hide_btn_input.clicked.connect(self.hide)
        input_row.addWidget(self.hide_btn_input)

        input_vlayout.addLayout(input_row)

        if self._hotkey_warning:
            warn_label = QLabel(self._hotkey_warning)
            warn_label.setWordWrap(True)
            warn_label.setStyleSheet(f"font-size: 11px; color: {WARNING_TEXT};")
            input_vlayout.addWidget(warn_label)

        card_layout.addWidget(self.input_container)

    def _setup_tray(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon = None
            return

        icon = self.style().standardIcon(self.style().StandardPixmap.SP_MessageBoxInformation)
        self.tray_icon = QSystemTrayIcon(icon, self)
        self.tray_icon.setToolTip(self._hotkey_label)

        menu = QMenu()
        menu.setStyleSheet(tray_menu_qss())
        toggle_action = QAction("Show / Hide", self)
        toggle_action.triggered.connect(self.toggle_visibility)
        menu.addAction(toggle_action)

        restart_action = QAction("Restart", self)
        restart_action.triggered.connect(self._on_restart_clicked)
        menu.addAction(restart_action)

        hotkey_action = QAction("Hotkey...", self)
        hotkey_action.triggered.connect(self.rebind_hotkey_requested.emit)
        menu.addAction(hotkey_action)

        menu.addSeparator()
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(QGuiApplication.quit)
        menu.addAction(quit_action)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def update_hotkey_label(self, pynput_hotkey: str) -> None:
        self._hotkey_label = format_hotkey_label(pynput_hotkey)
        self.title_label.setText(self._hotkey_label)
        self.hide_btn_answer.setToolTip("Hide")
        self.hide_btn_input.setToolTip("Hide")
        if getattr(self, "tray_icon", None) is not None:
            self.tray_icon.setToolTip(self._hotkey_label)

    def _anchor_bottom_left(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return
        geo = screen.availableGeometry()
        x = geo.left() + self._margin_x
        y = geo.bottom() - self.height() - self._margin_y + 1
        self.move(x, max(geo.top() + 8, y))

    def _enter_input_mode(self) -> None:
        self._in_answer_mode = False
        self.answer_container.hide()
        self.input_container.show()
        self.input_edit.setEnabled(True)
        self.send_btn.setEnabled(True)
        self.web_view.setHtml("")
        self.input_edit.setFocus()

    def _enter_answer_mode(self, html_content: str) -> None:
        self._in_answer_mode = True
        self.input_container.hide()
        self.answer_container.show()
        base_url = QUrl.fromLocalFile(str(PROJECT_ROOT) + "/")
        self.web_view.setHtml(html_content, base_url)
        if not self.isVisible():
            self.show()
        self.raise_()
        self.activateWindow()

    def _on_submit(self) -> None:
        if self._is_generating:
            return
        question = self.input_edit.text().strip()
        if not question:
            return

        self._is_generating = True
        self.input_edit.setEnabled(False)
        self.send_btn.setEnabled(False)

        self._worker_thread = QThread(self)
        self._worker = _QueryWorker(
            question=question,
            retriever=self.retriever,
            llm_client=self.llm_client,
            top_k=self._top_k,
        )
        self._worker.moveToThread(self._worker_thread)
        self._worker_thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_generation_finished)
        self._worker.failed.connect(self._on_generation_failed)
        self._worker.finished.connect(self._worker_thread.quit)
        self._worker.failed.connect(self._worker_thread.quit)
        self._worker_thread.finished.connect(self._cleanup_worker)
        self._worker_thread.start()

    def _cleanup_worker(self) -> None:
        if self._worker is not None:
            self._worker.deleteLater()
            self._worker = None
        if self._worker_thread is not None:
            self._worker_thread.deleteLater()
            self._worker_thread = None

    def _on_generation_finished(self, final_answer: str) -> None:
        self._is_generating = False
        rendered_html = render_answer_html(final_answer)
        self._enter_answer_mode(rendered_html)

    def _on_generation_failed(self, error_msg: str) -> None:
        self._is_generating = False
        safe_err = html.escape(error_msg)
        err_md = f"**Error**\n\n```\n{safe_err}\n```"
        rendered_html = render_answer_html(err_md)
        self._enter_answer_mode(rendered_html)

    def _on_restart_clicked(self) -> None:
        if self._is_generating:
            return
        self.input_edit.clear()
        self._enter_input_mode()
        if not self.isVisible():
            self.show()
        self.raise_()
        self.activateWindow()
        self.input_edit.setFocus()

    def restore_window(self) -> None:
        if not self.isVisible():
            self.show()
        self.raise_()
        self.activateWindow()
        if not self._in_answer_mode and self.input_edit.isEnabled():
            self.input_edit.setFocus()

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.restore_window()

    def _on_app_state_changed(self, state: Qt.ApplicationState) -> None:
        if state == Qt.ApplicationState.ApplicationActive and not self.isVisible():
            self.restore_window()

    def toggle_visibility(self) -> None:
        if self.isVisible():
            self.hide()
        else:
            self.restore_window()

    def changeEvent(self, event) -> None:
        if (
            event.type() == QEvent.Type.ActivationChange
            and not self.isActiveWindow()
            and self.isVisible()
            and QApplication.activePopupWidget() is None
            and QApplication.activeModalWidget() is None
        ):
            self.hide()
        super().changeEvent(event)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
            return
        super().keyPressEvent(event)

    def _hit_test_edges(self, pos: QPoint) -> tuple[bool, bool, bool, bool]:
        m = self._resize_margin
        w = self.width()
        h = self.height()
        left = pos.x() <= m
        right = pos.x() >= w - m
        top = pos.y() <= m
        bottom = pos.y() >= h - m
        return (left, right, top, bottom)

    @staticmethod
    def _cursor_for_edges(edges: tuple[bool, bool, bool, bool]) -> Qt.CursorShape:
        left, right, top, bottom = edges
        if (left and top) or (right and bottom):
            return Qt.CursorShape.SizeFDiagCursor
        if (right and top) or (left and bottom):
            return Qt.CursorShape.SizeBDiagCursor
        if left or right:
            return Qt.CursorShape.SizeHorCursor
        if top or bottom:
            return Qt.CursorShape.SizeVerCursor
        return Qt.CursorShape.ArrowCursor

    def resizeEvent(self, event) -> None:
        self._window_width = self.width()
        self._window_height = self.height()
        super().resizeEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            local_pos = event.position().toPoint()
            edges = self._hit_test_edges(local_pos)
            if any(edges):
                self._resize_edges = edges
                self._resize_start_pos = event.globalPosition().toPoint()
                self._resize_start_geo = self.geometry()
            else:
                self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if (
            self._resize_edges is not None
            and self._resize_start_pos is not None
            and self._resize_start_geo is not None
            and event.buttons() & Qt.MouseButton.LeftButton
        ):
            delta = event.globalPosition().toPoint() - self._resize_start_pos
            geo = QRect(self._resize_start_geo)
            left, right, top, bottom = self._resize_edges
            min_w = self.minimumWidth()
            min_h = self.minimumHeight()

            if left:
                new_left = min(geo.right() - min_w + 1, geo.left() + delta.x())
                geo.setLeft(new_left)
            if right:
                new_right = max(geo.left() + min_w - 1, geo.right() + delta.x())
                geo.setRight(new_right)
            if top:
                new_top = min(geo.bottom() - min_h + 1, geo.top() + delta.y())
                geo.setTop(new_top)
            if bottom:
                new_bottom = max(geo.top() + min_h - 1, geo.bottom() + delta.y())
                geo.setBottom(new_bottom)

            self.setGeometry(geo)
            event.accept()
            return

        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()
            return

        edges = self._hit_test_edges(event.position().toPoint())
        self.setCursor(self._cursor_for_edges(edges))
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._drag_offset = None
        self._resize_edges = None
        self._resize_start_pos = None
        self._resize_start_geo = None
        super().mouseReleaseEvent(event)
