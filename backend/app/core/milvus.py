"""Milvus Lite 向量库封装：连接、Collection 管理、混合检索、语义缓存。

- 文档库 document_chunks：text + dense(1024) + sparse(BM25/jieba)，供混合检索
- 缓存库 semantic_cache：query + answer + dense，供语义缓存（替代 Redis）
"""
from __future__ import annotations

from functools import lru_cache

from pymilvus import (
    AnnSearchRequest,
    DataType,
    Function,
    FunctionType,
    MilvusClient,
    RRFRanker,
)

from app.core.config import EMBED_DIM, settings

DOC_COLLECTION = "document_chunks"
CACHE_COLLECTION = "semantic_cache"
MAX_TEXT_LEN = 65535


@lru_cache
def get_milvus_client() -> MilvusClient:
    """返回进程内复用的 Milvus Lite 客户端（本地 .db 文件）。"""
    return MilvusClient(settings.milvus_db_abs)


def _truncate(text: str) -> str:
    return text[: MAX_TEXT_LEN - 1]


def init_collections() -> None:
    """创建所需 collection（幂等，可重复调用）。"""
    client = get_milvus_client()
    if not client.has_collection(DOC_COLLECTION):
        _create_doc_collection(client)
    if not client.has_collection(CACHE_COLLECTION):
        _create_cache_collection(client)
    # Milvus Lite 不持久化 load 状态，每个进程启动都需重新加载到内存后才能检索
    client.load_collection(DOC_COLLECTION)
    client.load_collection(CACHE_COLLECTION)


def _create_doc_collection(client: MilvusClient) -> None:
    schema = MilvusClient.create_schema(auto_id=True)
    schema.add_field("id", DataType.INT64, is_primary=True)
    schema.add_field("doc_id", DataType.VARCHAR, max_length=32)
    schema.add_field(
        "text",
        DataType.VARCHAR,
        max_length=MAX_TEXT_LEN,
        enable_analyzer=True,
        analyzer_params={"tokenizer": {"type": "jieba"}},
    )
    schema.add_field("dense", DataType.FLOAT_VECTOR, dim=EMBED_DIM)
    schema.add_field("sparse", DataType.SPARSE_FLOAT_VECTOR)
    # BM25 稀疏向量由 text 字段经 jieba 分词自动生成
    schema.add_function(
        Function(
            name="bm25",
            function_type=FunctionType.BM25,
            input_field_names=["text"],
            output_field_names=["sparse"],
        )
    )
    client.create_collection(DOC_COLLECTION, schema=schema)

    index = client.prepare_index_params()
    index.add_index(field_name="dense", index_type="FLAT", metric_type="COSINE")
    index.add_index(field_name="sparse", index_type="SPARSE_INVERTED_INDEX", metric_type="BM25")
    client.create_index(DOC_COLLECTION, index)
    client.load_collection(DOC_COLLECTION)


def _create_cache_collection(client: MilvusClient) -> None:
    schema = MilvusClient.create_schema(auto_id=True)
    schema.add_field("id", DataType.INT64, is_primary=True)
    schema.add_field("query", DataType.VARCHAR, max_length=1024)
    schema.add_field("answer", DataType.VARCHAR, max_length=MAX_TEXT_LEN)
    schema.add_field("dense", DataType.FLOAT_VECTOR, dim=EMBED_DIM)
    client.create_collection(CACHE_COLLECTION, schema=schema)

    index = client.prepare_index_params()
    index.add_index(field_name="dense", index_type="FLAT", metric_type="COSINE")
    client.create_index(CACHE_COLLECTION, index)
    client.load_collection(CACHE_COLLECTION)


# ---------------- 文档块写入 / 删除 ----------------


def insert_chunks(doc_id: int, chunks: list[str], vectors: list[list[float]]) -> None:
    if not chunks:
        return
    client = get_milvus_client()
    rows = [
        {"doc_id": str(doc_id), "text": _truncate(c), "dense": v}
        for c, v in zip(chunks, vectors)
    ]
    client.insert(DOC_COLLECTION, rows)


def delete_doc(doc_id: int) -> None:
    client = get_milvus_client()
    client.delete(DOC_COLLECTION, filter=f'doc_id == "{doc_id}"')


# ---------------- 检索 ----------------


def hybrid_search(query_embedding: list[float], query_text: str, top_k: int = 20) -> list[dict]:
    """稠密 + 稀疏（BM25）混合检索，RRF 融合，返回按相关度排序的文档块。"""
    client = get_milvus_client()
    dense_req = AnnSearchRequest(
        data=[query_embedding],
        anns_field="dense",
        param={"metric_type": "COSINE"},
        limit=top_k,
    )
    sparse_req = AnnSearchRequest(
        data=[query_text],
        anns_field="sparse",
        param={"metric_type": "BM25"},
        limit=top_k,
    )
    result = client.hybrid_search(
        DOC_COLLECTION,
        reqs=[dense_req, sparse_req],
        ranker=RRFRanker(60),
        limit=top_k,
        output_fields=["text", "doc_id"],
    )
    hits: list[dict] = []
    for hit in result[0]:
        entity = hit["entity"]
        hits.append(
            {
                "text": entity["text"],
                "doc_id": int(entity["doc_id"]),
                "score": round(hit["distance"], 4),
            }
        )
    return hits


# ---------------- 语义缓存 ----------------


def cache_lookup(query_embedding: list[float], threshold: float = 0.92) -> str | None:
    """按查询向量找语义最相近的已缓存问答，超过阈值则命中返回答案。"""
    client = get_milvus_client()
    result = client.search(
        CACHE_COLLECTION,
        data=[query_embedding],
        anns_field="dense",
        limit=1,
        output_fields=["answer"],
    )
    if not result or not result[0]:
        return None
    hit = result[0][0]
    if hit["distance"] >= threshold:
        return hit["entity"]["answer"]
    return None


def cache_insert(query: str, answer: str, query_embedding: list[float]) -> None:
    client = get_milvus_client()
    client.insert(
        CACHE_COLLECTION,
        [{"query": query, "answer": answer, "dense": query_embedding}],
    )


def recommend_questions(
    query_embedding: list[float], top_k: int = 3, threshold: float = 0.65
) -> list[str]:
    """在语义缓存里检索与当前问题相近的历史提问，用于「相似问题推荐」。"""
    client = get_milvus_client()
    result = client.search(
        CACHE_COLLECTION,
        data=[query_embedding],
        anns_field="dense",
        limit=top_k + 2,
        output_fields=["query"],
    )
    if not result or not result[0]:
        return []
    seen: set[str] = set()
    out: list[str] = []
    for hit in result[0]:
        if hit["distance"] < threshold:
            continue
        q = hit["entity"].get("query")
        if q and q not in seen:
            seen.add(q)
            out.append(q)
        if len(out) >= top_k:
            break
    return out