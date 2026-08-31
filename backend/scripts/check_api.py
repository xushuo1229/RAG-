"""百炼 API 连通性验证：LLM 流式对话 / Embedding / Rerank 三件套。"""
import os
import sys
import time

import httpx
from dotenv import load_dotenv  # noqa: F401  (pydantic-settings 已处理，此处不依赖)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.core.config import settings  # noqa: E402

OK = "\033[92m[PASS]\033[0m"
FAIL = "\033[91m[FAIL]\033[0m"

headers = {"Authorization": f"Bearer {settings.dashscope_api_key}"}


def check_llm():
    url = f"{settings.llm_base_url}/chat/completions"
    body = {
        "model": settings.llm_model,
        "messages": [
            {"role": "system", "content": "你是电商客服助手，用一句话回答。"},
            {"role": "user", "content": "你好，请做个自我介绍"},
        ],
        "stream": False,
        "max_tokens": 100,
        # qwen3.x 系列默认开启思考模式，问答场景需要显式关闭
        "enable_thinking": False,
    }
    t0 = time.time()
    r = httpx.post(url, json=body, headers=headers, timeout=60)
    dt = time.time() - t0
    if r.status_code == 200:
        data = r.json()
        content = data["choices"][0]["message"].get("content", "")
        print(f"{OK} LLM {settings.llm_model} ({dt:.1f}s): {content[:60]}...")
        return True
    print(f"{FAIL} LLM HTTP {r.status_code}: {r.text[:300]}")
    return False


def check_embedding():
    url = f"{settings.llm_base_url}/embeddings"
    body = {"model": settings.embedding_model, "input": ["静音降噪蓝牙耳机", "全棉四件套床品"], "dimension": 1024}
    t0 = time.time()
    r = httpx.post(url, json=body, headers=headers, timeout=60)
    dt = time.time() - t0
    if r.status_code == 200:
        data = r.json()
        vec = data["data"][0]["embedding"]
        print(f"{OK} Embedding {settings.embedding_model} ({dt:.1f}s): dim={len(vec)}, 前3维={[round(x, 4) for x in vec[:3]]}")
        return True
    print(f"{FAIL} Embedding HTTP {r.status_code}: {r.text[:300]}")
    return False


def check_rerank():
    url = f"{settings.dashscope_base_url}/services/rerank/text-rerank/text-rerank"
    body = {
        "model": settings.rerank_model,
        "input": {
            "query": "耳机的续航时间多长",
            "documents": [
                "本耳机支持主动降噪，续航可达 40 小时。",
                "床品四件套采用新疆长绒棉，亲肤透气。",
                "充电 10 分钟可使用 5 小时，支持快充。",
            ],
        },
        "parameters": {"return_documents": True, "top_n": 3},
    }
    t0 = time.time()
    r = httpx.post(url, json=body, headers=headers, timeout=60)
    dt = time.time() - t0
    if r.status_code == 200:
        data = r.json()
        results = data["output"]["results"]
        order = [res["index"] for res in results]
        print(f"{OK} Rerank {settings.rerank_model} ({dt:.1f}s): 文档排序={order} (期望 [0,2,1])")
        return True
    print(f"{FAIL} Rerank HTTP {r.status_code}: {r.text[:300]}")
    return False


if __name__ == "__main__":
    print(f"LLM 端点  : {settings.llm_base_url}")
    print(f"DashScope : {settings.dashscope_base_url}")
    print("-" * 60)
    results = [check_llm(), check_embedding(), check_rerank()]
    print("-" * 60)
    print("全部通过" if all(results) else "存在失败项，见上方 [FAIL]")
    sys.exit(0 if all(results) else 1)
