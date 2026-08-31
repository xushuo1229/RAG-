"""文档入库编排：落盘 -> 解析 -> 切分 -> 向量化 -> 写入 Milvus。"""
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.milvus import delete_doc, insert_chunks
from app.models.document import Document
from app.services.embedding import embed_texts
from app.services.loader import SUPPORTED, parse_content, split_text


def create_and_process(db: Session, filename: str, content: bytes) -> Document:
    """新建文档记录并完成整条入库流水线；失败时标记 failed 并保留记录。"""
    doc = Document(filename=filename, file_type=filename.rsplit(".", 1)[-1].lower(), size=len(content))
    db.add(doc)
    db.commit()
    db.refresh(doc)

    dest = Path(settings.upload_abs) / f"{doc.id}_{filename}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(content)

    try:
        text = parse_content(dest, filename)
        chunks = split_text(text)
        vectors = embed_texts(chunks)
        insert_chunks(doc.id, chunks, vectors)
        doc.chunk_count = len(chunks)
        doc.status = "ready"
        doc.error = ""
    except Exception as exc:  # noqa: BLE001 解析/向量化失败需落库展示
        doc.status = "failed"
        doc.error = str(exc)[:500]
    db.commit()
    db.refresh(doc)
    return doc


def remove_document(db: Session, doc: Document) -> None:
    """删除文档：清理向量 + 关系库记录 + 本地文件。"""
    delete_doc(doc.id)
    db.delete(doc)
    db.commit()
    local = Path(settings.upload_abs) / f"{doc.id}_{doc.filename}"
    local.unlink(missing_ok=True)