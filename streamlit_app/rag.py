"""RAG pipeline with DeepSeek API (China-friendly, near-free) + pgvector retrieval."""

import re
from openai import OpenAI

CITATION_PATTERN = re.compile(r"\[来源(\d+)\]")

SYSTEM_PROMPT = """你是专业的财税知识助手。请基于以下参考资料回答用户的问题。

要求：
1. 回答必须基于提供的参考资料，不要编造信息
2. 引用来源时使用 [来源N] 标记，N 为参考资料的编号
3. 如果参考资料不足以回答问题，请如实说明
4. 回答要简洁、准确、有条理
5. 如果用户要求修改、更新或删除某条知识，请说明可以在左侧"知识管理"中操作"""

DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"


def build_context(chunks: list[dict]) -> tuple[str, dict[int, dict]]:
    parts = []
    citation_map = {}
    for i, chunk in enumerate(chunks, 1):
        source_title = chunk.get("source_title", "未知")
        page_info = f" 第{chunk['page_number']}页" if chunk.get("page_number") else ""
        parts.append(f"[来源{i} - {source_title}{page_info}]\n{chunk['content']}")
        citation_map[i] = {
            "chunk_id": chunk["chunk_id"],
            "source_type": chunk["source_type"],
            "source_id": chunk["source_id"],
            "source_title": source_title,
            "snippet": chunk["content"][:200],
            "page_number": chunk.get("page_number"),
            "section_title": chunk.get("section_title"),
            "sheet_name": chunk.get("sheet_name"),
            "row_number": chunk.get("row_number"),
            "relevance_score": chunk.get("score", 0),
        }
    return "\n\n".join(parts), citation_map


def extract_citations(text: str, citation_map: dict[int, dict]) -> list[dict]:
    cited_indices = set(int(m) for m in CITATION_PATTERN.findall(text))
    return [citation_map[idx] for idx in sorted(cited_indices) if idx in citation_map]


def rag_stream(query: str, module_id: str, api_key: str):
    """Yields (event_type, data) tuples for streaming RAG responses."""
    from kb import search

    search_results = search(query, module_id=module_id, top_k=8)

    if not search_results:
        yield ("content", "抱歉，知识库中没有找到与您问题相关的参考资料。请先上传文件或添加知识条目。")
        yield ("citations", [])
        return

    context, citation_map = build_context(search_results)
    user_message = f"参考资料：\n{context}\n\n用户问题：{query}"

    client = OpenAI(api_key=api_key, base_url=DEEPSEEK_BASE_URL)

    full_text = ""
    try:
        stream = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            stream=True,
            max_tokens=2048,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                full_text += delta
                yield ("content", delta)
    except Exception as e:
        yield ("content", f"生成失败: {e}")
        yield ("citations", [])
        return

    citations = extract_citations(full_text, citation_map)
    yield ("citations", citations)
    yield ("full_text", full_text)
