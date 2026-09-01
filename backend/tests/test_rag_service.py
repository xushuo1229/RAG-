"""测试 app/services/rag_service.py：提示词拼接、去重、检索编排（全部 mock，不碰真实向量库/大模型）。"""
from app.services import rag_service


def test_build_prompt_contains_context_and_question():
    """拼接后的提示词应同时包含参考资料与用户问题。"""
    prompt = rag_service.build_prompt("参考资料正文", "如何退货？")
    assert "参考资料正文" in prompt
    assert "如何退货？" in prompt


def test_dedupe_removes_duplicate_prefix():
    """文本前 50 字符相同的文档块应被去重，只保留第一条。"""
    long_prefix = "苹果支持七天无理由退货，" * 6  # 超过 50 字符的相同前缀
    hits = [
        {"text": long_prefix + "结尾A", "doc_id": 1},
        {"text": long_prefix + "结尾B", "doc_id": 2},
        {"text": "另一条", "doc_id": 3},
    ]
    result = rag_service._dedupe(hits)
    assert len(result) == 2


def test_retrieve_returns_sources_and_context(monkeypatch):
    """检索编排：召回 -> 去重 -> 重排 -> 生成来源与上下文，全程 mock。"""
    monkeypatch.setattr(rag_service, "embed_query", lambda q: [0.1, 0.2])
    monkeypatch.setattr(
        rag_service,
        "hybrid_search",
        lambda emb, q, top_k: [{"text": "苹果支持七天无理由退货", "doc_id": 3, "score": 0.9}],
    )
    monkeypatch.setattr(rag_service, "rerank", lambda q, texts, top_n: [(0, "苹果支持七天无理由退货")])

    sources, context = rag_service.retrieve("如何退货？", {3: "售后政策.txt"})

    assert len(sources) == 1
    assert sources[0].filename == "售后政策.txt"
    assert sources[0].doc_id == 3
    assert "苹果支持七天无理由退货" in context


def test_retrieve_empty_hits(monkeypatch):
    """召回为空时直接返回空来源与空上下文，不应调用重排。"""
    monkeypatch.setattr(rag_service, "embed_query", lambda q: [0.1])
    monkeypatch.setattr(rag_service, "hybrid_search", lambda emb, q, top_k: [])
    called = {"rerank": False}

    def _rerank(q, texts, top_n):
        called["rerank"] = True
        return []

    monkeypatch.setattr(rag_service, "rerank", _rerank)

    sources, context = rag_service.retrieve("问题", {})
    assert sources == []
    assert context == ""
    assert called["rerank"] is False