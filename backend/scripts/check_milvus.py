"""Milvus Lite 混合检索验证：稠密向量 + BM25 稀疏（jieba 中文分词）+ RRF 融合。"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.core.config import settings  # noqa: E402

from pymilvus import AnnSearchRequest, DataType, Function, FunctionType, MilvusClient, RRFRanker

docs = [
    "这款蓝牙耳机支持主动降噪，单次续航 40 小时，搭配充电仓总续航 120 小时。",
    "四件套床品采用新疆长绒棉，A 类母婴级面料，亲肤透气不起球。",
    "耳机支持快充：充电 10 分钟听歌 5 小时，IPX5 防水防汗适合运动。",
    "保温杯采用 316 不锈钢内胆，24 小时保温，容量 500ml。",
]


def main():
    db_path = settings.milvus_db_abs
    client = MilvusClient(db_path)
    print(f"已连接 Milvus Lite: {db_path}")

    col = "smoke_test"
    if client.has_collection(col):
        client.drop_collection(col)

    schema = MilvusClient.create_schema(auto_id=True)
    schema.add_field("id", DataType.INT64, is_primary=True)
    schema.add_field(
        "text",
        DataType.VARCHAR,
        max_length=65535,
        enable_analyzer=True,
        analyzer_params={"tokenizer": {"type": "jieba"}},
    )
    schema.add_field("dense", DataType.FLOAT_VECTOR, dim=4)
    schema.add_field("sparse", DataType.SPARSE_FLOAT_VECTOR)
    schema.add_function(
        Function(
            name="bm25",
            function_type=FunctionType.BM25,
            input_field_names=["text"],
            output_field_names=["sparse"],
        )
    )

    client.create_collection(col, schema=schema)
    index = client.prepare_index_params()
    index.add_index(field_name="dense", index_type="FLAT", metric_type="COSINE")
    index.add_index(field_name="sparse", index_type="SPARSE_INVERTED_INDEX", metric_type="BM25")
    client.create_index(col, index)
    client.load_collection(col)

    import random

    random.seed(42)
    rows = [
        {"text": t, "dense": [random.random() for _ in range(4)]} for t in docs
    ]
    client.insert(col, rows)
    print(f"已插入 {len(rows)} 条测试文档（含中文电商商品描述）")

    dense_req = AnnSearchRequest(
        data=[[0.1, 0.2, 0.3, 0.4]], anns_field="dense", param={"metric_type": "COSINE"}, limit=4
    )
    sparse_req = AnnSearchRequest(data=["耳机续航时间"], anns_field="sparse", param={"metric_type": "BM25"}, limit=4)
    results = client.hybrid_search(
        col, reqs=[dense_req, sparse_req], ranker=RRFRanker(60), limit=4, output_fields=["text"]
    )
    print("混合检索（查询: 耳机续航时间）命中:")
    for hit in results[0]:
        print(f"  score={hit['distance']:.4f} | {hit['entity']['text'][:40]}")

    client.drop_collection(col)
    print("清理测试 collection 完成，Milvus Lite 混合检索可用")


if __name__ == "__main__":
    main()
