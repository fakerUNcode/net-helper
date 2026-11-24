from __future__ import annotations

# ColaMD Theme: 羊皮纸 Sepia 色彩与排版令牌
BG_COLOR = "#f6efe0"
BG_CARD_RGBA = "rgba(246, 239, 224, 245)"
BG_INPUT = "#efe6d0"
BG_INPUT_FOCUS = "#fbf6eb"
BG_MUTED = "#ece2cb"
TEXT_COLOR = "#4f4032"
TEXT_SECONDARY = "#7b6b54"
TEXT_MUTED = "#9a8a72"
BORDER_COLOR = "#e2d7bf"
BORDER_STRONG = "#c9a86a"
BORDER_CARD = "#d9cbb0"
LINK_COLOR = "#9c5e29"
LINK_HOVER = "#844e20"
CODE_TEXT = "#7a5a33"
CODE_BG = "rgba(122, 90, 51, 0.1)"
CODE_BLOCK_BG = "#ece2cb"
BLOCKQUOTE_BORDER = "#c9a86a"
BLOCKQUOTE_BG = "#efe6d0"
TABLE_HEADER_BG = "#ece2cb"
SELECTION_BG = "rgba(160, 98, 45, 0.15)"
SELECTION_QT_BG = "rgba(160, 98, 45, 0.22)"
HIGHLIGHT_BG = "#f2dfa8"

BUTTON_TEXT_ON_ACCENT = "#fcf8ef"
SUCCESS_TEXT = "#3f6a3e"
WARNING_TEXT = "#9c5e29"
DOWNLOAD_BTN_BG = "#5b7447"
DOWNLOAD_BTN_HOVER = "#4b6239"

SERIF_FONT_FAMILY = "Georgia, 'Source Han Serif SC', 'Noto Serif SC', 'Songti SC', serif"
QT_SERIF_FONT_FAMILY = 'Georgia, "Source Han Serif SC", "Noto Serif SC", "Songti SC", serif'


def secondary_button_qss(*, border_radius: int = 6, padding: str = "3px 8px", font_size: int = 11) -> str:
    return f"""
        QPushButton {{
            background: {BG_INPUT};
            color: {TEXT_COLOR};
            border: 1px solid {BORDER_COLOR};
            border-radius: {border_radius}px;
            padding: {padding};
            font-size: {font_size}px;
        }}
        QPushButton:hover {{
            background: {BORDER_COLOR};
            border-color: {BORDER_STRONG};
        }}
    """


def ghost_icon_button_qss(*, border_radius: int = 6, font_size: int = 12) -> str:
    return f"""
        QPushButton {{
            background: {CODE_BG};
            color: {TEXT_SECONDARY};
            border: 1px solid {BORDER_COLOR};
            border-radius: {border_radius}px;
            font-size: {font_size}px;
        }}
        QPushButton:hover {{
            background: {BORDER_COLOR};
            color: {TEXT_COLOR};
            border-color: {BORDER_STRONG};
        }}
    """


def accent_button_qss(*, border_radius: int = 8, padding: str = "0px", font_size: int = 13) -> str:
    return f"""
        QPushButton {{
            background: {LINK_COLOR};
            color: {BUTTON_TEXT_ON_ACCENT};
            border: none;
            border-radius: {border_radius}px;
            padding: {padding};
            font-size: {font_size}px;
            font-weight: 600;
        }}
        QPushButton:hover {{
            background: {LINK_HOVER};
        }}
        QPushButton:disabled {{
            background: {BORDER_COLOR};
            color: {TEXT_MUTED};
        }}
    """


def tray_menu_qss() -> str:
    return f"""
        QMenu {{
            background-color: {BG_COLOR};
            color: {TEXT_COLOR};
            border: 1px solid {BORDER_COLOR};
            border-radius: 8px;
            padding: 4px;
        }}
        QMenu::item {{
            padding: 6px 14px;
            border-radius: 5px;
        }}
        QMenu::item:selected {{
            background-color: {HIGHLIGHT_BG};
            color: {TEXT_COLOR};
        }}
        QMenu::separator {{
            height: 1px;
            background: {BORDER_COLOR};
            margin: 4px 8px;
        }}
    """


def message_box_qss() -> str:
    return f"""
        QMessageBox {{
            background-color: {BG_COLOR};
            color: {TEXT_COLOR};
        }}
        QMessageBox QLabel {{
            color: {TEXT_COLOR};
        }}
        QMessageBox QPushButton {{
            background: {BG_INPUT};
            color: {TEXT_COLOR};
            border: 1px solid {BORDER_COLOR};
            border-radius: 6px;
            padding: 5px 14px;
            min-width: 64px;
        }}
        QMessageBox QPushButton:hover {{
            background: {BORDER_COLOR};
            border-color: {BORDER_STRONG};
        }}
        QMessageBox QPushButton:default {{
            background: {LINK_COLOR};
            color: {BUTTON_TEXT_ON_ACCENT};
            border: none;
        }}
        QMessageBox QPushButton:default:hover {{
            background: {LINK_HOVER};
        }}
    """
