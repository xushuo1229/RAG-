"""文本向量化：调用阿里云百炼 text-embedding-v4（OpenAI 兼容端点）。"""
import httpx

from app.core.config import EMBED_DIM, settings

BATCH_SIZE = 16


def embed_texts(texts: list[str]) -> list[list[float]]:
    """批量向量化，返回与原列表一一对应的 1024 维向量。"""
    if not texts:
        return []
    url = f"{settings.llm_base_url}/embeddings"
    headers = {"Authorization": f"Bearer {settings.dashscope_api_key}"}

    vectors: list[list[float]] = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        body = {"model": settings.embedding_model, "input": batch, "dimension": EMBED_DIM}
        r = httpx.post(url, json=body, headers=headers, timeout=120)
        r.raise_for_status()
        data = r.json()
        for item in data["data"]:
            vectors.append(item["embedding"])
    return vectors


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]