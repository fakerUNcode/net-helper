from __future__ import annotations

import html
import re
from pathlib import Path

import markdown
from pygments.formatters import HtmlFormatter

from rag.config import PROJECT_ROOT
from ui.theme import (
    BG_COLOR,
    BLOCKQUOTE_BG,
    BLOCKQUOTE_BORDER,
    BORDER_COLOR,
    CODE_BG,
    CODE_BLOCK_BG,
    CODE_TEXT,
    HIGHLIGHT_BG,
    LINK_COLOR,
    SELECTION_BG,
    SERIF_FONT_FAMILY,
    TABLE_HEADER_BG,
    TEXT_COLOR,
    TEXT_MUTED,
    TEXT_SECONDARY,
)

_CODE_AND_MATH_RE = re.compile(
    r"(```[\s\S]*?```|`[^`\n]+`|\$\$[\s\S]*?\$\$|(?<!\\)\$(?!\$)(?:\\.|[^\n$\\])+(?<!\\)\$(?!\$))"
)


def _get_mathjax_script_tag() -> str:
    local_candidates = [
        PROJECT_ROOT / "assets" / "mathjax" / "es5" / "tex-mml-chtml.js",
        PROJECT_ROOT / "assets" / "mathjax" / "tex-mml-chtml.js",
    ]
    for path in local_candidates:
        if path.exists():
            return f'<script defer src="{path.as_uri()}"></script>'
    return (
        '<script defer id="MathJax-script" '
        'src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>'
    )


def _protect_math_outside_code(md_text: str) -> tuple[str, dict[str, str]]:
    """在 Markdown 解析前保护 LaTeX 公式，防止 _ * \\ 等符号被 Markdown 破坏。"""
    placeholders: dict[str, str] = {}
    counter = 0

    def _repl(match: re.Match[str]) -> str:
        nonlocal counter
        token = match.group(0)
        if token.startswith("`"):
            return token
        key = f"@@MATH_PLACEHOLDER_{counter}@@"
        counter += 1
        placeholders[key] = html.escape(token, quote=False)
        return key

    protected = _CODE_AND_MATH_RE.sub(_repl, md_text)
    return protected, placeholders


def render_answer_html(markdown_text: str) -> str:
    """将完整答案渲染为包含 Markdown、代码高亮与 MathJax 3 的透明背景 HTML。"""
    protected_md, placeholders = _protect_math_outside_code(markdown_text)

    body_html = markdown.markdown(
        protected_md,
        extensions=[
            "fenced_code",
            "codehilite",
            "tables",
            "sane_lists",
            "nl2br",
        ],
        extension_configs={
            "codehilite": {
                "css_class": "codehilite",
                "guess_lang": False,
                "noclasses": False,
            }
        },
    )

    for key, escaped_math in placeholders.items():
        body_html = body_html.replace(key, escaped_math)

    pygments_css = HtmlFormatter(style="gruvbox-light").get_style_defs(".codehilite")
    mathjax_tag = _get_mathjax_script_tag()

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<script>
window.MathJax = {{
  tex: {{
    inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
    displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']],
    processEscapes: true
  }},
  options: {{
    skipHtmlTags: ['script', 'noscript', 'style', 'textarea', 'pre', 'code']
  }}
}};
</script>
{mathjax_tag}
<style>
  :root {{
    --bg-color: {BG_COLOR};
    --text-color: {TEXT_COLOR};
    --text-secondary: {TEXT_SECONDARY};
    --text-muted: {TEXT_MUTED};
    --border-color: {BORDER_COLOR};
    --link-color: {LINK_COLOR};
    --code-bg: {CODE_BG};
    --code-block-bg: {CODE_BLOCK_BG};
    --blockquote-border: {BLOCKQUOTE_BORDER};
    --blockquote-bg: {BLOCKQUOTE_BG};
    --table-header-bg: {TABLE_HEADER_BG};
    --selection-bg: {SELECTION_BG};
    --highlight-bg: {HIGHLIGHT_BG};
  }}
  html, body {{
    margin: 0;
    padding: 0;
    height: 100%;
    background: transparent;
    color: var(--text-color);
    font-family: {SERIF_FONT_FAMILY};
    font-size: 13.5px;
    line-height: 1.85;
    overflow-x: hidden;
    overflow-y: auto;
    overflow-wrap: break-word;
  }}
  ::selection {{
    background: var(--selection-bg);
  }}
  #content {{
    padding: 6px 12px 12px 12px;
  }}
  p {{
    margin: 0 0 8px 0;
  }}
  p:last-child {{
    margin-bottom: 0;
  }}
  a {{
    color: var(--link-color);
    text-decoration: underline;
    text-underline-offset: 2px;
  }}
  mark {{
    background: var(--highlight-bg);
    color: var(--text-color);
    padding: 0 2px;
    border-radius: 2px;
  }}
  h1, h2, h3, h4 {{
    margin: 10px 0 6px 0;
    color: var(--text-color);
    font-weight: 600;
  }}
  h1 {{
    font-size: 17px;
    text-align: center;
    border-bottom: none;
    letter-spacing: 0.02em;
  }}
  h2 {{
    font-size: 15.5px;
    border-bottom: 1px dashed var(--border-color);
    padding-bottom: 4px;
  }}
  h3 {{ font-size: 14.5px; }}
  hr {{
    border: none;
    border-top: 1px dashed var(--border-color);
    margin: 12px 0;
  }}
  ul, ol {{
    margin: 4px 0 8px 0;
    padding-left: 20px;
  }}
  li {{
    margin: 2px 0;
  }}
  code {{
    font-family: "JetBrains Mono", "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
    font-size: 12.5px;
    background: var(--code-bg);
    padding: 1px 5px;
    border-radius: 4px;
    color: {CODE_TEXT};
  }}
  pre, .codehilite pre {{
    background: var(--code-block-bg);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 10px 12px;
    overflow-x: auto;
    margin: 8px 0;
    font-size: 12.5px;
    line-height: 1.5;
    color: var(--text-color);
  }}
  pre code, .codehilite pre code {{
    background: transparent;
    padding: 0;
    color: inherit;
  }}
  table {{
    border-collapse: collapse;
    width: 100%;
    margin: 8px 0;
    font-size: 13px;
  }}
  th, td {{
    border: 1px solid var(--border-color);
    padding: 5px 8px;
    text-align: left;
  }}
  th {{
    background: var(--table-header-bg);
    color: var(--text-color);
  }}
  blockquote {{
    margin: 8px 0;
    padding: 6px 20px 6px 24px;
    border-left: 3px solid var(--blockquote-border);
    background: var(--blockquote-bg);
    color: var(--text-secondary);
    border-radius: 0 6px 6px 0;
  }}
  mjx-container {{
    color: var(--text-color);
    overflow-x: auto;
    max-width: 100%;
  }}
  ::-webkit-scrollbar {{
    width: 6px;
    height: 6px;
  }}
  ::-webkit-scrollbar-thumb {{
    background: rgba(122, 90, 51, 0.25);
    border-radius: 3px;
  }}
  ::-webkit-scrollbar-thumb:hover {{
    background: rgba(122, 90, 51, 0.4);
  }}
  ::-webkit-scrollbar-track {{
    background: transparent;
  }}
  {pygments_css}
  .codehilite {{
    background: transparent;
  }}
</style>
</head>
<body>
  <div id="content">{body_html}</div>
</body>
</html>"""
