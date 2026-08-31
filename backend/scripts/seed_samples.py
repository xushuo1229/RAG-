"""导入电商样例数据到知识库（等价于在管理页逐个上传样例文件）。"""
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.database import SessionLocal, init_db  # noqa: E402
from app.core.milvus import init_collections  # noqa: E402
from app.services.document_service import create_and_process  # noqa: E402

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "data" / "samples"


def main() -> None:
    init_db()
    init_collections()
    files = [f for f in sorted(SAMPLE_DIR.glob("*")) if f.suffix.lower() in {".txt", ".md"}]
    if not files:
        print(f"样例目录为空：{SAMPLE_DIR}")
        return

    with SessionLocal() as db:
        ok = 0
        for f in files:
            doc = create_and_process(db, f.name, f.read_bytes())
            if doc.status == "ready":
                ok += 1
                print(f"[OK ] {f.name} -> {doc.chunk_count} chunks")
            else:
                print(f"[FAIL] {f.name} -> {doc.error}")
        print(f"\n完成：{ok}/{len(files)} 个样例文档入库成功")


if __name__ == "__main__":
    main()