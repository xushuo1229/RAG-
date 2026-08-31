"""重排序：调用阿里云百炼 gte-rerank-v2（DashScope 原生端点）。"""
import httpx

from app.core.config import settings


def rerank(query: str, documents: list[str], top_n: int = 4) -> list[tuple[int, str]]:
    """对候选文档按与查询的相关性重排，返回 [(原始索引, 文本)] 降序。"""
    if not documents:
        return []
    url = f"{settings.dashscope_base_url}/services/rerank/text-rerank/text-rerank"
    headers = {"Authorization": f"Bearer {settings.dashscope_api_key}"}
    body = {
        "model": settings.rerank_model,
        "input": {"query": query, "documents": documents},
        "parameters": {"return_documents": True, "top_n": min(top_n, len(documents))},
    }
    r = httpx.post(url, json=body, headers=headers, timeout=60)
    r.raise_for_status()
    results = r.json()["output"]["results"]
    out: list[tuple[int, str]] = []
    for res in results:
        doc = res.get("document")
        # return_documents=True 时 document 为 {"text": "..."} 结构
        text = doc.get("text", "") if isinstance(doc, dict) else (doc or "")
        out.append((res["index"], text))
    return out