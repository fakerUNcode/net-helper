from __future__ import annotations

import html
import re
from pathlib import Path

import markdown
from pygments.formatters import HtmlFormatter

from rag.config import PROJECT_ROOT

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

    pygments_css = HtmlFormatter(style="monokai").get_style_defs(".codehilite")
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
  html, body {{
    margin: 0;
    padding: 0;
    height: 100%;
    background: transparent;
    color: #f3f4f6;
    font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", "Segoe UI", Roboto, sans-serif;
    font-size: 13.5px;
    line-height: 1.55;
    overflow-x: hidden;
    overflow-y: auto;
    overflow-wrap: break-word;
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
  h1, h2, h3, h4 {{
    margin: 10px 0 6px 0;
    color: #ffffff;
    font-weight: 600;
  }}
  h1 {{ font-size: 17px; }}
  h2 {{ font-size: 15.5px; }}
  h3 {{ font-size: 14.5px; }}
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
    background: rgba(255, 255, 255, 0.12);
    padding: 1px 5px;
    border-radius: 4px;
    color: #93c5fd;
  }}
  pre, .codehilite pre {{
    background: rgba(15, 17, 23, 0.85);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 8px;
    padding: 10px 12px;
    overflow-x: auto;
    margin: 8px 0;
    font-size: 12.5px;
    line-height: 1.45;
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
    border: 1px solid rgba(255, 255, 255, 0.18);
    padding: 5px 8px;
    text-align: left;
  }}
  th {{
    background: rgba(255, 255, 255, 0.10);
  }}
  blockquote {{
    margin: 6px 0;
    padding: 4px 10px;
    border-left: 3px solid #60a5fa;
    background: rgba(96, 165, 250, 0.08);
    color: #e5e7eb;
  }}
  mjx-container {{
    color: #f9fafb;
    overflow-x: auto;
    max-width: 100%;
  }}
  ::-webkit-scrollbar {{
    width: 6px;
    height: 6px;
  }}
  ::-webkit-scrollbar-thumb {{
    background: rgba(255, 255, 255, 0.22);
    border-radius: 3px;
  }}
  ::-webkit-scrollbar-track {{
    background: transparent;
  }}
  {pygments_css}
</style>
</head>
<body>
  <div id="content">{body_html}</div>
</body>
</html>"""
