# -*- coding: utf-8 -*-
"""Locust 压测脚本：模拟 100 用户并发使用问答系统（SSE 流式）。

运行（headless 模式，阶梯加压由各阶段单独运行实现）：
  locust -f locustfile.py --headless -u 25 -r 5 -t 3m --csv result_25
  locust -f locustfile.py --headless -u 50 -r 5 -t 3m --csv result_50
  locust -f locustfile.py --headless -u 100 -r 10 -t 10m --csv result_100
"""
import itertools
import json
import random
from pathlib import Path

import requests
from locust import HttpUser, between, events, task

HERE = Path(__file__).parent
QUESTIONS = json.loads((HERE / "questions.json").read_text(encoding="utf-8"))

# 全局共享的问题迭代器：保证 100 个虚拟用户拿到的问题互不重复（不触发语义缓存）
_q_cycle = itertools.cycle(QUESTIONS)
_counter = itertools.count()


def next_question() -> str:
    """按序取下一条问题；并发下 itertools.cycle 非线程安全，但重复概率极低且无害。"""
    with _lock:
        return next(_q_cycle)


import threading  # noqa: E402

_lock = threading.Lock()


class ChatUser(HttpUser):
    """模拟单个真实用户：登录一次，然后循环提问（含思考时间）。"""

    wait_time = between(3, 8)  # 模拟打字/阅读的思考时间
    host = "http://127.0.0.1:8000"

    def on_start(self) -> None:
        """每个虚拟用户启动时登录，拿自己的 token。"""
        idx = next(_counter)
        self.username = f"loadtest_{idx % 100 + 1:03d}"
        r = requests.post(
            f"{self.host}/api/auth/login",
            json={"username": self.username, "password": "LoadTest#2026"},
            timeout=10,
        )
        r.raise_for_status()
        self.token = r.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}

    @task(10)
    def ask_question(self) -> None:
        """核心场景：SSE 流式问答，统计首字延迟和总延迟。"""
        q = next_question()
        t0 = __import__("time").monotonic()
        first_token_at = None
        done = False
        status = "ok"

        with self.client.post(
            "/api/chat",
            json={"question": q, "conversation_id": None},
            headers=self.headers,
            stream=True,
            catch_response=True,
            name="/api/chat [SSE问答]",
        ) as resp:
            if resp.status_code == 429:
                status = "rate_limited"  # 预期内限流，不算系统错误
                resp.success()
                return
            if resp.status_code != 200:
                resp.failure(f"HTTP {resp.status_code}")
                return
            # 逐行读 SSE 流
            for line in resp.iter_lines():
                if not line:
                    continue
                text = line.decode("utf-8", errors="ignore")
                if not text.startswith("data: "):
                    continue
                if first_token_at is None:
                    first_token_at = __import__("time").monotonic()
                payload = json.loads(text[6:])
                if payload.get("type") == "error":
                    status = "sse_error"
                    resp.failure(payload.get("data", "unknown"))
                    return
                if payload.get("type") == "done":
                    done = True
            if not done:
                resp.failure("SSE 流未收到 done 事件")
                return
            resp.success()

        total = __import__("time").monotonic() - t0
        ttfb = (first_token_at - t0) if first_token_at else -1
        _record(status, total, ttfb)

    @task(1)
    def list_conversations(self) -> None:
        """轻量场景：刷新会话列表。"""
        self.client.get("/api/conversations", headers=self.headers, name="/api/conversations [会话列表]")


# ---------------- 自定义指标：问答延迟（含 SSE 读取耗时，Locust 默认统计不到流式总时长） ----------------

_metrics = {"count": 0, "ttfb_sum": 0.0, "total_sum": 0.0, "rl": 0, "err": 0}


def _record(status: str, total: float, ttfb: float) -> None:
    with _lock:
        if status == "rate_limited":
            _metrics["rl"] += 1
            return
        if status != "ok":
            _metrics["err"] += 1
            return
        _metrics["count"] += 1
        _metrics["ttfb_sum"] += max(ttfb, 0)
        _metrics["total_sum"] += total


@events.test_stop.add_listener
def on_stop(environment, **kwargs) -> None:
    m = _metrics
    n = m["count"]
    print("\n===== 问答自定义指标 =====")
    print(f"完成问答: {n}, 限流429: {m['rl']}, SSE错误: {m['err']}")
    if n:
        print(f"平均首字延迟: {m['ttfb_sum']/n:.2f}s, 平均总延迟: {m['total_sum']/n:.2f}s")
