"""轻量 RAG 检索评测：自建电商 QA 对，计算命中率 HitRate@k 与 MRR。

不调用 LLM，不产生额外费用；如需评测答案质量，可再扩展 faithfulness 指标。
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.database import SessionLocal, init_db  # noqa: E402
from app.core.milvus import init_collections  # noqa: E402
from app.models.document import Document  # noqa: E402
from app.services.rag_service import retrieve  # noqa: E402
from sqlalchemy import select  # noqa: E402

# 每条：问题 -> 期望命中的文档名关键词
QA = [
    {"q": "这款蓝牙耳机的续航时间是多长？", "doc": "蓝牙耳机"},
    {"q": "蓝牙耳机支持快充吗，充多久能用？", "doc": "蓝牙耳机"},
    {"q": "四件套是什么面料，安全等级如何？", "doc": "四件套"},
    {"q": "四件套夏天买哪款比较凉快？", "doc": "四件套"},
    {"q": "保温杯内胆是什么材质，保温多久？", "doc": "保温杯"},
    {"q": "保温杯容量是多少？", "doc": "保温杯"},
    {"q": "支持七天无理由退货吗？", "doc": "售后"},
    {"q": "多少金额可以包邮？", "doc": "售后"},
]


def main() -> None:
    init_db()
    init_collections()
    with SessionLocal() as db:
        doc_name_map = {d.id: d.filename for d in db.scalars(select(Document)).all()}

    hit = 0
    mrr_sum = 0.0
    total = len(QA)
    for qa in QA:
        sources, _ = retrieve(qa["q"], doc_name_map)
        fnames = [s.filename for s in sources]
        rank = next((i for i, fn in enumerate(fnames) if qa["doc"] in fn), None)
        if rank is not None:
            hit += 1
            mrr_sum += 1 / (rank + 1)
        print(f"Q: {qa['q']}")
        print(f"   期望文档【{qa['doc']}】命中:{rank is not None}  排序:{rank}  返回:{[f.split('_')[0] for f in fnames[:4]]}")

    hit_rate = hit / total
    mrr = mrr_sum / total
    print("\n" + "=" * 50)
    print(f"评测集规模     : {total} 条")
    print(f"命中率 HitRate : {hit_rate:.2%}")
    print(f"平均倒数排名 MRR : {mrr:.3f}")


if __name__ == "__main__":
    main()