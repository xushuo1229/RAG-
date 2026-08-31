"""RAG 检索与上下文编排：混合检索 -> 重排 -> 拼接提示词。"""
from app.core.milvus import hybrid_search
from app.schemas.chat import SourceOut
from app.services.embedding import embed_query
from app.services.rerank import rerank

SYSTEM_PROMPT = (
    "你是电商商品知识库的智能问答助手。请严格依据下方【参考资料】回答用户问题，"
    "回答要准确、简洁、口语化，使用中文。如果资料中没有相关信息，请明确说"
    "“知识库中暂无相关信息”，不要编造或猜测。"
)

RETRIEVE_TOP_K = 8
RERANK_TOP_N = 4


def build_prompt(context: str, question: str) -> str:
    return f"【参考资料】\n{context}\n\n【用户问题】\n{question}"


def _dedupe(hits: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for h in hits:
        key = h["text"][:50]
        if key in seen:
            continue
        seen.add(key)
        out.append(h)
    return out


def retrieve(query: str, doc_name_map: dict[int, str]) -> tuple[list[SourceOut], str]:
    """召回 -> 重排，返回引用来源列表与拼接好的上下文文本。"""
    q_embedding = embed_query(query)
    hits = _dedupe(hybrid_search(q_embedding, query, top_k=RETRIEVE_TOP_K))

    texts = [h["text"] for h in hits]
    ranked = rerank(query, texts, top_n=RERANK_TOP_N) if texts else []

    sources: list[SourceOut] = []
    chunks: list[str] = []
    for idx, text in ranked:
        hit = hits[idx]
        sources.append(
            SourceOut(
                doc_id=hit["doc_id"],
                filename=doc_name_map.get(hit["doc_id"], f"文档{hit['doc_id']}"),
                text=text,
                score=hit["score"],
            )
        )
        chunks.append(text)

    context = "\n\n".join(f"[{i + 1}] {t}" for i, t in enumerate(chunks))
    return sources, context