"""LLM 流式生成：调用阿里云百炼 qwen-plus（OpenAI 兼容 /chat/completions）。"""
import json
from collections.abc import Iterator

import httpx

from app.core.config import settings


def stream_chat(
    messages: list[dict],
    temperature: float = 0.3,
    max_tokens: int = 1024,
) -> Iterator[str]:
    """流式对话，逐段 yield 文本增量。"""
    url = f"{settings.llm_base_url}/chat/completions"
    headers = {"Authorization": f"Bearer {settings.dashscope_api_key}"}
    body = {
        "model": settings.llm_model,
        "messages": messages,
        "stream": True,
        "temperature": temperature,
        "max_tokens": max_tokens,
        # qwen 系列默认开启思考模式，问答场景需显式关闭，否则会输出 reasoning
        "enable_thinking": False,
    }
    with httpx.stream("POST", url, json=body, headers=headers, timeout=120) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines():
            line = line.strip()
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if payload == "[DONE]":
                break
            try:
                obj = json.loads(payload)
            except json.JSONDecodeError:
                continue
            delta = obj["choices"][0].get("delta", {}).get("content")
            if delta:
                yield delta


def build_messages(system: str, history: list[dict], question: str) -> list[dict]:
    """组装 messages：system + 历史多轮 + 当前问题。"""
    messages = [{"role": "system", "content": system}]
    for turn in history[-6:]:  # 仅保留最近 6 条历史，控制上下文
        messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({"role": "user", "content": question})
    return messages