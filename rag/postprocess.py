from __future__ import annotations

import re

_BANNED_PREFIX_RE = re.compile(
    r"^(?:"
    r"根据(?:提供的|上述|参考)?资料(?:可知|显示|表明|如下)?[，,：:\s]*|"
    r"综上所述[，,：:\s]*|"
    r"需要注意的是[，,：:\s]*|"
    r"值得注意的是[，,：:\s]*|"
    r"由上述内容可知[，,：:\s]*"
    r")+",
    flags=re.MULTILINE,
)

_CODE_SEGMENT_RE = re.compile(r"(```[\s\S]*?```|`[^`\n]+`)")


def _normalize_latex_in_prose(text: str) -> str:
    # \[ ... \] -> $$ ... $$
    def _replace_display(match: re.Match[str]) -> str:
        inner = match.group(1).strip()
        if "\n" in inner:
            return f"\n$$\n{inner}\n$$\n"
        return f"$$\n{inner}\n$$"

    text = re.sub(r"\\\[([\s\S]*?)\\\]", _replace_display, text)

    # \( ... \) -> $...$
    def _replace_inline(match: re.Match[str]) -> str:
        inner = match.group(1).strip()
        return f"${inner}$"

    text = re.sub(r"\\\(([\s\S]*?)\\\)", _replace_inline, text)

    # 规范化单行 $ ... $ 首尾多余空格，避免 MathJax 误判
    text = re.sub(
        r"(?<!\$)\$(?!\$)[ \t]*([^\n$]+?)[ \t]*(?<!\$)\$(?!\$)",
        lambda m: f"${m.group(1).strip()}$",
        text,
    )
    return text


def postprocess_answer(raw_text: str) -> str:
    """答案后处理器：去除多余空行、规范化 LaTeX、剔除残留套话前缀。"""
    if not raw_text:
        return ""

    text = raw_text.replace("\r\n", "\n").replace("\r", "\n").strip()

    # 仅在非代码块区域规范化 LaTeX 与套话
    segments = _CODE_SEGMENT_RE.split(text)
    processed_segments: list[str] = []
    for idx, seg in enumerate(segments):
        if idx % 2 == 1:
            # 代码块 / 行内代码原样保留
            processed_segments.append(seg)
        else:
            cleaned = _normalize_latex_in_prose(seg)
            if idx == 0:
                cleaned = _BANNED_PREFIX_RE.sub("", cleaned).lstrip()
            processed_segments.append(cleaned)

    result = "".join(processed_segments)
    # 去除多余空行（3个及以上换行压缩为2个）
    result = re.sub(r"\n{3,}", "\n\n", result)
    # 去除行尾多余空格（保留 Markdown 双空格换行除外，这里统一清理多余空白）
    result = "\n".join(line.rstrip() for line in result.splitlines())
    return result.strip()
