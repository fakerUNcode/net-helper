from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ThemePalette:
    key: str
    label: str
    is_dark: bool
    bg_color: str
    bg_card_rgba: str
    bg_input: str
    bg_input_focus: str
    bg_muted: str
    text_color: str
    text_secondary: str
    text_muted: str
    border_color: str
    border_strong: str
    border_card: str
    link_color: str
    link_hover: str
    code_text: str
    code_bg: str
    code_block_bg: str
    code_block_text: str
    blockquote_border: str
    blockquote_bg: str
    table_header_bg: str
    selection_bg: str
    selection_qt_bg: str
    highlight_bg: str
    button_text_on_accent: str
    warning_text: str
    download_btn_bg: str
    download_btn_hover: str
    font_family: str
    qt_font_family: str
    pygments_style: str


_DEFAULT_SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Noto Sans SC', sans-serif"
_DEFAULT_QT_SANS = '"-apple-system", "Segoe UI", "PingFang SC", "Noto Sans SC", sans-serif'
_SERIF_FONT = "Georgia, 'Source Han Serif SC', 'Noto Serif SC', 'Songti SC', serif"
_QT_SERIF_FONT = 'Georgia, "Source Han Serif SC", "Noto Serif SC", "Songti SC", serif'
_ELEGANT_FONT = "'LXGW WenKai', 'Noto Serif SC', 'Source Han Serif SC', 'Songti SC', Georgia, serif"
_QT_ELEGANT_FONT = '"LXGW WenKai", "Noto Serif SC", "Source Han Serif SC", "Songti SC", Georgia, serif'
_WRITER_FONT = "'SF Mono', 'JetBrains Mono', 'Fira Code', Menlo, Consolas, 'PingFang SC', 'Noto Sans SC', monospace"
_QT_WRITER_FONT = '"SF Mono", "JetBrains Mono", "Fira Code", Menlo, Consolas, "PingFang SC", "Noto Sans SC", monospace'


THEMES: dict[str, ThemePalette] = {
    "sepia": ThemePalette(
        key="sepia",
        label="Sepia",
        is_dark=False,
        bg_color="#f6efe0",
        bg_card_rgba="rgba(246, 239, 224, 245)",
        bg_input="#efe6d0",
        bg_input_focus="#fbf6eb",
        bg_muted="#ece2cb",
        text_color="#4f4032",
        text_secondary="#7b6b54",
        text_muted="#9a8a72",
        border_color="#e2d7bf",
        border_strong="#c9a86a",
        border_card="#d9cbb0",
        link_color="#9c5e29",
        link_hover="#844e20",
        code_text="#7a5a33",
        code_bg="rgba(122, 90, 51, 0.1)",
        code_block_bg="#ece2cb",
        code_block_text="#4f4032",
        blockquote_border="#c9a86a",
        blockquote_bg="#efe6d0",
        table_header_bg="#ece2cb",
        selection_bg="rgba(160, 98, 45, 0.15)",
        selection_qt_bg="rgba(160, 98, 45, 0.22)",
        highlight_bg="#f2dfa8",
        button_text_on_accent="#fcf8ef",
        warning_text="#9c5e29",
        download_btn_bg="#5b7447",
        download_btn_hover="#4b6239",
        font_family=_SERIF_FONT,
        qt_font_family=_QT_SERIF_FONT,
        pygments_style="gruvbox-light",
    ),
    "light": ThemePalette(
        key="light",
        label="Light",
        is_dark=False,
        bg_color="#ffffff",
        bg_card_rgba="rgba(255, 255, 255, 245)",
        bg_input="#f6f8fa",
        bg_input_focus="#ffffff",
        bg_muted="#eef1f4",
        text_color="#24292f",
        text_secondary="#656d76",
        text_muted="#656d76",
        border_color="#d0d7de",
        border_strong="#8c959f",
        border_card="#d0d7de",
        link_color="#0969da",
        link_hover="#0550ae",
        code_text="#24292f",
        code_bg="rgba(175, 184, 193, 0.2)",
        code_block_bg="#f6f8fa",
        code_block_text="#24292f",
        blockquote_border="#d0d7de",
        blockquote_bg="#f6f8fa",
        table_header_bg="#f6f8fa",
        selection_bg="rgba(9, 105, 218, 0.15)",
        selection_qt_bg="rgba(9, 105, 218, 0.22)",
        highlight_bg="#fff3bf",
        button_text_on_accent="#ffffff",
        warning_text="#9a6700",
        download_btn_bg="#1f883d",
        download_btn_hover="#1a7f37",
        font_family=_DEFAULT_SANS,
        qt_font_family=_DEFAULT_QT_SANS,
        pygments_style="default",
    ),
    "elegant": ThemePalette(
        key="elegant",
        label="Elegant",
        is_dark=False,
        bg_color="#f0edea",
        bg_card_rgba="rgba(240, 237, 234, 245)",
        bg_input="#eae6e1",
        bg_input_focus="#f7f4f1",
        bg_muted="#e8e4df",
        text_color="#2c2c2c",
        text_secondary="#6c6c6c",
        text_muted="#777777",
        border_color="#d8d3ce",
        border_strong="#c44b2b",
        border_card="#d8d3ce",
        link_color="#bc4424",
        link_hover="#9e381d",
        code_text="#c44b2b",
        code_bg="#e8e4df",
        code_block_bg="#2c2c2c",
        code_block_text="#e0dcd7",
        blockquote_border="#c44b2b",
        blockquote_bg="#eae6e1",
        table_header_bg="#eae6e1",
        selection_bg="rgba(196, 75, 43, 0.2)",
        selection_qt_bg="rgba(196, 75, 43, 0.25)",
        highlight_bg="#f0d9a8",
        button_text_on_accent="#ffffff",
        warning_text="#bc4424",
        download_btn_bg="#4a7c59",
        download_btn_hover="#3d684a",
        font_family=_ELEGANT_FONT,
        qt_font_family=_QT_ELEGANT_FONT,
        pygments_style="monokai",
    ),
    "notion": ThemePalette(
        key="notion",
        label="Notion",
        is_dark=False,
        bg_color="#ffffff",
        bg_card_rgba="rgba(255, 255, 255, 245)",
        bg_input="#f7f6f3",
        bg_input_focus="#ffffff",
        bg_muted="#f1f0ec",
        text_color="#37352f",
        text_secondary="#777674",
        text_muted="#9b9a97",
        border_color="#e9e9e7",
        border_strong="#37352f",
        border_card="#e3e3e0",
        link_color="#37352f",
        link_hover="#1f1e1a",
        code_text="#eb5757",
        code_bg="#f7f6f3",
        code_block_bg="#f7f6f3",
        code_block_text="#37352f",
        blockquote_border="#37352f",
        blockquote_bg="#f7f6f3",
        table_header_bg="#f7f6f3",
        selection_bg="rgba(35, 131, 226, 0.14)",
        selection_qt_bg="rgba(35, 131, 226, 0.22)",
        highlight_bg="#fdecc8",
        button_text_on_accent="#ffffff",
        warning_text="#d9730d",
        download_btn_bg="#2383e2",
        download_btn_hover="#1a6fc4",
        font_family=_DEFAULT_SANS,
        qt_font_family=_DEFAULT_QT_SANS,
        pygments_style="default",
    ),
    "writer": ThemePalette(
        key="writer",
        label="Writer",
        is_dark=False,
        bg_color="#fcfcfa",
        bg_card_rgba="rgba(252, 252, 250, 245)",
        bg_input="#f2f2ee",
        bg_input_focus="#ffffff",
        bg_muted="#eaeae4",
        text_color="#1a1a1a",
        text_secondary="#757571",
        text_muted="#8e8e8a",
        border_color="#e3e3de",
        border_strong="#1a1a1a",
        border_card="#dcdcd6",
        link_color="#3b6ec4",
        link_hover="#2d57a0",
        code_text="#1a1a1a",
        code_bg="rgba(0, 0, 0, 0.05)",
        code_block_bg="#f2f2ee",
        code_block_text="#1a1a1a",
        blockquote_border="#1a1a1a",
        blockquote_bg="#f2f2ee",
        table_header_bg="#f2f2ee",
        selection_bg="rgba(59, 110, 196, 0.15)",
        selection_qt_bg="rgba(59, 110, 196, 0.22)",
        highlight_bg="#fff3a3",
        button_text_on_accent="#ffffff",
        warning_text="#b26a00",
        download_btn_bg="#3b6ec4",
        download_btn_hover="#2d57a0",
        font_family=_WRITER_FONT,
        qt_font_family=_QT_WRITER_FONT,
        pygments_style="default",
    ),
    "bear": ThemePalette(
        key="bear",
        label="Bear",
        is_dark=False,
        bg_color="#ffffff",
        bg_card_rgba="rgba(255, 255, 255, 245)",
        bg_input="#f7f5f3",
        bg_input_focus="#ffffff",
        bg_muted="#efeae6",
        text_color="#262626",
        text_secondary="#767676",
        text_muted="#8a8a8a",
        border_color="#e8e6e3",
        border_strong="#d43d2a",
        border_card="#e8e6e3",
        link_color="#d43d2a",
        link_hover="#b33120",
        code_text="#d43d2a",
        code_bg="rgba(212, 61, 42, 0.07)",
        code_block_bg="#2e2a28",
        code_block_text="#efe9e4",
        blockquote_border="#d43d2a",
        blockquote_bg="#f7f5f3",
        table_header_bg="#f7f5f3",
        selection_bg="rgba(212, 61, 42, 0.12)",
        selection_qt_bg="rgba(212, 61, 42, 0.20)",
        highlight_bg="#ffe9a8",
        button_text_on_accent="#ffffff",
        warning_text="#d43d2a",
        download_btn_bg="#5b7447",
        download_btn_hover="#4b6239",
        font_family=_DEFAULT_SANS,
        qt_font_family=_DEFAULT_QT_SANS,
        pygments_style="monokai",
    ),
    "dark": ThemePalette(
        key="dark",
        label="Dark",
        is_dark=True,
        bg_color="#0d1117",
        bg_card_rgba="rgba(13, 17, 23, 245)",
        bg_input="#161b22",
        bg_input_focus="#1c2128",
        bg_muted="#21262d",
        text_color="#e6edf3",
        text_secondary="#aab3bd",
        text_muted="#8b949e",
        border_color="#30363d",
        border_strong="#58a6ff",
        border_card="#30363d",
        link_color="#58a6ff",
        link_hover="#79c0ff",
        code_text="#e6edf3",
        code_bg="rgba(110, 118, 129, 0.3)",
        code_block_bg="#161b22",
        code_block_text="#e6edf3",
        blockquote_border="#30363d",
        blockquote_bg="#161b22",
        table_header_bg="#161b22",
        selection_bg="rgba(88, 166, 255, 0.2)",
        selection_qt_bg="rgba(88, 166, 255, 0.28)",
        highlight_bg="rgba(210, 153, 34, 0.35)",
        button_text_on_accent="#0d1117",
        warning_text="#d29922",
        download_btn_bg="#238636",
        download_btn_hover="#2ea043",
        font_family=_DEFAULT_SANS,
        qt_font_family=_DEFAULT_QT_SANS,
        pygments_style="monokai",
    ),
    "midnight": ThemePalette(
        key="midnight",
        label="Midnight",
        is_dark=True,
        bg_color="#000000",
        bg_card_rgba="rgba(0, 0, 0, 245)",
        bg_input="#111111",
        bg_input_focus="#1a1a1a",
        bg_muted="#1a1a1a",
        text_color="#d6d6d6",
        text_secondary="#b1b1b1",
        text_muted="#7a7a7a",
        border_color="#262626",
        border_strong="#0a84ff",
        border_card="#262626",
        link_color="#0a84ff",
        link_hover="#409cff",
        code_text="#d6d6d6",
        code_bg="rgba(255, 255, 255, 0.08)",
        code_block_bg="#111111",
        code_block_text="#d6d6d6",
        blockquote_border="#3a3a3a",
        blockquote_bg="#111111",
        table_header_bg="#111111",
        selection_bg="rgba(10, 132, 255, 0.28)",
        selection_qt_bg="rgba(10, 132, 255, 0.35)",
        highlight_bg="rgba(255, 214, 10, 0.25)",
        button_text_on_accent="#ffffff",
        warning_text="#ffd60a",
        download_btn_bg="#30d158",
        download_btn_hover="#28b84c",
        font_family=_DEFAULT_SANS,
        qt_font_family=_DEFAULT_QT_SANS,
        pygments_style="monokai",
    ),
    "solarized-dark": ThemePalette(
        key="solarized-dark",
        label="Solarized Dark",
        is_dark=True,
        bg_color="#002b36",
        bg_card_rgba="rgba(0, 43, 54, 245)",
        bg_input="#073642",
        bg_input_focus="#0a4352",
        bg_muted="#073642",
        text_color="#c2d5d7",
        text_secondary="#a4bbc3",
        text_muted="#586e75",
        border_color="#0d3d4a",
        border_strong="#2aa198",
        border_card="#0d3d4a",
        link_color="#3093da",
        link_hover="#52a8e5",
        code_text="#2aa198",
        code_bg="rgba(88, 110, 117, 0.22)",
        code_block_bg="#073642",
        code_block_text="#c2d5d7",
        blockquote_border="#2aa198",
        blockquote_bg="#073642",
        table_header_bg="#073642",
        selection_bg="rgba(38, 139, 210, 0.25)",
        selection_qt_bg="rgba(38, 139, 210, 0.35)",
        highlight_bg="rgba(181, 137, 0, 0.3)",
        button_text_on_accent="#ffffff",
        warning_text="#b58900",
        download_btn_bg="#2aa198",
        download_btn_hover="#228b83",
        font_family=_DEFAULT_SANS,
        qt_font_family=_DEFAULT_QT_SANS,
        pygments_style="monokai",
    ),
    "nord": ThemePalette(
        key="nord",
        label="Nord",
        is_dark=True,
        bg_color="#2e3440",
        bg_card_rgba="rgba(46, 52, 64, 245)",
        bg_input="#262c37",
        bg_input_focus="#3b4252",
        bg_muted="#3b4252",
        text_color="#d8dee9",
        text_secondary="#aebdd4",
        text_muted="#7d8ba1",
        border_color="#3b4252",
        border_strong="#81a1c1",
        border_card="#434c5e",
        link_color="#88c0d0",
        link_hover="#9fd0de",
        code_text="#88c0d0",
        code_bg="rgba(136, 192, 208, 0.12)",
        code_block_bg="#262c37",
        code_block_text="#d8dee9",
        blockquote_border="#81a1c1",
        blockquote_bg="#262c37",
        table_header_bg="#3b4252",
        selection_bg="rgba(136, 192, 208, 0.2)",
        selection_qt_bg="rgba(136, 192, 208, 0.3)",
        highlight_bg="rgba(235, 203, 139, 0.25)",
        button_text_on_accent="#2e3440",
        warning_text="#ebcb8b",
        download_btn_bg="#a3be8c",
        download_btn_hover="#8fae76",
        font_family=_DEFAULT_SANS,
        qt_font_family=_DEFAULT_QT_SANS,
        pygments_style="monokai",
    ),
    "gruvbox": ThemePalette(
        key="gruvbox",
        label="Gruvbox",
        is_dark=True,
        bg_color="#282828",
        bg_card_rgba="rgba(40, 40, 40, 245)",
        bg_input="#1d2021",
        bg_input_focus="#32302f",
        bg_muted="#3c3836",
        text_color="#ebdbb2",
        text_secondary="#c5b5a5",
        text_muted="#928374",
        border_color="#3c3836",
        border_strong="#fe8019",
        border_card="#504945",
        link_color="#83a598",
        link_hover="#9ab8ac",
        code_text="#b8bb26",
        code_bg="rgba(235, 219, 178, 0.1)",
        code_block_bg="#1d2021",
        code_block_text="#ebdbb2",
        blockquote_border="#fe8019",
        blockquote_bg="#1d2021",
        table_header_bg="#3c3836",
        selection_bg="rgba(254, 128, 25, 0.2)",
        selection_qt_bg="rgba(254, 128, 25, 0.3)",
        highlight_bg="rgba(250, 189, 47, 0.22)",
        button_text_on_accent="#282828",
        warning_text="#fabd2f",
        download_btn_bg="#98971a",
        download_btn_hover="#b8bb26",
        font_family=_DEFAULT_SANS,
        qt_font_family=_DEFAULT_QT_SANS,
        pygments_style="monokai",
    ),
    "dracula": ThemePalette(
        key="dracula",
        label="Dracula",
        is_dark=True,
        bg_color="#282a36",
        bg_card_rgba="rgba(40, 42, 54, 245)",
        bg_input="#21222c",
        bg_input_focus="#343746",
        bg_muted="#343746",
        text_color="#f8f8f2",
        text_secondary="#afb7db",
        text_muted="#7f86a8",
        border_color="#44475a",
        border_strong="#ff79c6",
        border_card="#44475a",
        link_color="#bd93f9",
        link_hover="#cca9fa",
        code_text="#8be9fd",
        code_bg="rgba(98, 114, 164, 0.2)",
        code_block_bg="#21222c",
        code_block_text="#f8f8f2",
        blockquote_border="#ff79c6",
        blockquote_bg="#21222c",
        table_header_bg="#343746",
        selection_bg="rgba(189, 147, 249, 0.25)",
        selection_qt_bg="rgba(189, 147, 249, 0.35)",
        highlight_bg="rgba(241, 250, 140, 0.22)",
        button_text_on_accent="#282a36",
        warning_text="#ffb86c",
        download_btn_bg="#50fa7b",
        download_btn_hover="#3ae366",
        font_family=_DEFAULT_SANS,
        qt_font_family=_DEFAULT_QT_SANS,
        pygments_style="monokai",
    ),
}

THEME_ORDER: list[str] = [
    "sepia",
    "light",
    "elegant",
    "notion",
    "writer",
    "bear",
    "dark",
    "midnight",
    "solarized-dark",
    "nord",
    "gruvbox",
    "dracula",
]

DEFAULT_THEME_KEY = "sepia"
_ACTIVE_THEME_KEY = DEFAULT_THEME_KEY


def get_theme(key: str | None = None) -> ThemePalette:
    if key is None:
        return THEMES[_ACTIVE_THEME_KEY]
    normalized = str(key).strip().lower()
    return THEMES.get(normalized, THEMES[DEFAULT_THEME_KEY])


def set_active_theme(key: str | None) -> ThemePalette:
    global _ACTIVE_THEME_KEY
    palette = get_theme(key)
    _ACTIVE_THEME_KEY = palette.key
    return palette


def get_active_theme() -> ThemePalette:
    return THEMES[_ACTIVE_THEME_KEY]


def secondary_button_qss(
    *,
    theme: ThemePalette | None = None,
    border_radius: int = 6,
    padding: str = "3px 8px",
    font_size: int = 11,
) -> str:
    t = theme or get_active_theme()
    return f"""
        QPushButton {{
            background: {t.bg_input};
            color: {t.text_color};
            border: 1px solid {t.border_color};
            border-radius: {border_radius}px;
            padding: {padding};
            font-size: {font_size}px;
        }}
        QPushButton:hover {{
            background: {t.bg_muted};
            border-color: {t.border_strong};
        }}
    """


def ghost_icon_button_qss(
    *,
    theme: ThemePalette | None = None,
    border_radius: int = 6,
    font_size: int = 12,
) -> str:
    t = theme or get_active_theme()
    return f"""
        QPushButton {{
            background: {t.code_bg};
            color: {t.text_secondary};
            border: 1px solid {t.border_color};
            border-radius: {border_radius}px;
            font-size: {font_size}px;
        }}
        QPushButton:hover {{
            background: {t.bg_muted};
            color: {t.text_color};
            border-color: {t.border_strong};
        }}
    """


def accent_button_qss(
    *,
    theme: ThemePalette | None = None,
    border_radius: int = 8,
    padding: str = "0px",
    font_size: int = 13,
) -> str:
    t = theme or get_active_theme()
    return f"""
        QPushButton {{
            background: {t.link_color};
            color: {t.button_text_on_accent};
            border: none;
            border-radius: {border_radius}px;
            padding: {padding};
            font-size: {font_size}px;
            font-weight: 600;
        }}
        QPushButton:hover {{
            background: {t.link_hover};
        }}
        QPushButton:disabled {{
            background: {t.border_color};
            color: {t.text_muted};
        }}
    """


def combo_box_qss(theme: ThemePalette | None = None) -> str:
    t = theme or get_active_theme()
    return f"""
        QComboBox {{
            background: {t.bg_input};
            color: {t.text_color};
            border: 1px solid {t.border_color};
            border-radius: 8px;
            padding: 6px 10px;
            font-size: 13px;
        }}
        QComboBox:focus, QComboBox:hover {{
            border: 1px solid {t.link_color};
            background: {t.bg_input_focus};
        }}
        QComboBox::drop-down {{
            border: none;
            width: 24px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {t.bg_color};
            color: {t.text_color};
            border: 1px solid {t.border_color};
            selection-background-color: {t.highlight_bg};
            selection-color: {t.text_color};
            outline: 0;
        }}
    """


def tray_menu_qss(theme: ThemePalette | None = None) -> str:
    t = theme or get_active_theme()
    return f"""
        QMenu {{
            background-color: {t.bg_color};
            color: {t.text_color};
            border: 1px solid {t.border_color};
            border-radius: 8px;
            padding: 4px;
        }}
        QMenu::item {{
            padding: 6px 14px;
            border-radius: 5px;
        }}
        QMenu::item:selected {{
            background-color: {t.highlight_bg};
            color: {t.text_color};
        }}
        QMenu::separator {{
            height: 1px;
            background: {t.border_color};
            margin: 4px 8px;
        }}
    """


def message_box_qss(theme: ThemePalette | None = None) -> str:
    t = theme or get_active_theme()
    return f"""
        QMessageBox {{
            background-color: {t.bg_color};
            color: {t.text_color};
        }}
        QMessageBox QLabel {{
            color: {t.text_color};
        }}
        QMessageBox QPushButton {{
            background: {t.bg_input};
            color: {t.text_color};
            border: 1px solid {t.border_color};
            border-radius: 6px;
            padding: 5px 14px;
            min-width: 64px;
        }}
        QMessageBox QPushButton:hover {{
            background: {t.bg_muted};
            border-color: {t.border_strong};
        }}
        QMessageBox QPushButton:default {{
            background: {t.link_color};
            color: {t.button_text_on_accent};
            border: none;
        }}
        QMessageBox QPushButton:default:hover {{
            background: {t.link_hover};
        }}
    """
