from __future__ import annotations

from rag.retriever import RetrievedChunk

SYSTEM_PROMPT_TEMPLATE = """你是一个高精度、零废话的知识库问答引擎。你必须严格遵守以下规则：
1. 【严格忠于资料】仅允许依据下方提供的【参考资料】作答，严禁使用资料之外的知识或凭空编造。若参考资料不足以回答问题，仅输出：`资料库中未包含该问题的相关信息。`
2. 【最短作答原则】输出能彻底解决问题且不遗漏任何核心要点的最小答案。直接给出结论、公式、步骤或代码。
3. 【绝对禁止项】
   - 禁止寒暄、客套、开场白、结束语与总结句。
   - 禁止重复表述、禁止举例说明（除非题目本身要求代码/公式）、禁止解释背景知识。
   - 严禁出现“根据资料”“根据上述内容”“综上所述”“需要注意的是”“值得注意的是”“希望能帮到你”等任何过渡废话。
4. 【格式规范】使用标准 Markdown；行内数学公式使用 `$...$`，独立公式块使用 `$$...$$`；代码使用标准 Markdown 代码块。"""

USER_PROMPT_TEMPLATE = """【参考资料】
{context}

【问题】
{question}

【最小完整答案】"""


def build_messages(question: str, chunks: list[RetrievedChunk]) -> list[dict[str, str]]:
    """Prompt 组装器：将 Top-K 检索片段与硬编码最短作答指令注入对话消息。"""
    if not chunks:
        context_block = "（无相关资料）"
    else:
        sections: list[str] = []
        for idx, chunk in enumerate(chunks, start=1):
            sections.append(
                f"[片段 {idx} | 来源: {chunk.source_file} | chunk_id: {chunk.chunk_id}]\n{chunk.text}"
            )
        context_block = "\n\n---\n\n".join(sections)

    user_content = USER_PROMPT_TEMPLATE.format(
        context=context_block,
        question=question.strip(),
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT_TEMPLATE},
        {"role": "user", "content": user_content},
    ]
