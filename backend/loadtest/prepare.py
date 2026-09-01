# -*- coding: utf-8 -*-
"""压测数据准备：注册 100 个压测账号 + 生成不重复问题集（用完可通过 cleanup.py 清理）。"""
import json
import random
import sys
from pathlib import Path

import requests

BASE = "http://127.0.0.1:8000"
HERE = Path(__file__).parent

# ---------------- 1. 注册压测账号 ----------------

PREFIX = "loadtest_"
PASSWORD = "LoadTest#2026"
COUNT = int(sys.argv[1]) if len(sys.argv) > 1 else 100


def register_accounts(count: int) -> None:
    """注册 loadtest_001 ~ loadtest_{count}，已存在则跳过。"""
    ok = skip = fail = 0
    for i in range(1, count + 1):
        username = f"{PREFIX}{i:03d}"
        r = requests.post(
            f"{BASE}/api/auth/register",
            json={"username": username, "password": PASSWORD},
            timeout=10,
        )
        if r.status_code == 201:
            ok += 1
        elif r.status_code == 409:
            skip += 1  # 上次压测遗留，直接复用
        else:
            fail += 1
            print(f"  注册失败 {username}: {r.status_code} {r.text[:100]}")
    print(f"账号准备完成: 新注册 {ok}, 复用 {skip}, 失败 {fail}")


# ---------------- 2. 生成不重复问题集 ----------------

# 模板围绕知识库 4 个文档的主题（商品规格/售后物流/会员/退换货），变量组合保证不重复
PRODUCTS = ["保温杯", "蓝牙耳机", "运动鞋", "背包", "台灯", "加湿器", "充电宝", "键盘"]
ATTRS = [
    "容量是多少", "电池续航多久", "材质是什么", "防水等级是多少", "重量是多少",
    "有哪些颜色", "尺寸是多少", "保修期多长", "支持退换货吗", "有优惠活动吗",
    "怎么清洗保养", "发货后多久能到", "包装里有什么配件", "适合什么场景使用",
    "和上一代有什么区别", "充电要多久", "售后电话是多少", "能用优惠券吗",
    "新疆西藏能发货吗", "七天无理由退货怎么算",
]
PATTERNS = [
    "{p}的{a}？",
    "请问{p}{a}呢",
    "我想了解一下{p}的{a}",
    "客服你好，{p}{a}",
    "帮我查下{p}{a}，谢谢",
]


def build_questions() -> list[str]:
    """生成不重复问题集：5 模板 × 8 商品 × 20 属性，打乱后取 350 条。"""
    qs = [t.format(p=p, a=a) for t in PATTERNS for p in PRODUCTS for a in ATTRS]
    random.Random(42).shuffle(qs)
    return qs[:350]


def main() -> None:
    register_accounts(COUNT)
    questions = build_questions()
    (HERE / "questions.json").write_text(
        json.dumps(questions, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(f"问题集生成完成: {len(questions)} 条 -> questions.json")


if __name__ == "__main__":
    main()
