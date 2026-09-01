"""测试 app/services/document_service.py：文档入库编排与删除（mock 向量库与外部接口）。"""
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.services import document_service


def _db() -> MagicMock:
    """构造一个假的数据库会话，refresh 时为文档补充自增 id。"""
    db = MagicMock()
    db.refresh.side_effect = lambda doc: setattr(doc, "id", 1)
    return db


def test_create_and_process_success(monkeypatch, tmp_path):
    """完整入库流水线成功：状态 ready、块数量正确、向量已写入。"""
    db = _db()
    # 把上传目录指向临时目录，避免污染真实 data/uploads
    monkeypatch.setattr(document_service, "settings", SimpleNamespace(upload_abs=str(tmp_path)))
    monkeypatch.setattr(document_service, "parse_content", lambda path, filename: "正文")
    monkeypatch.setattr(document_service, "split_text", lambda text: ["块1", "块2"])
    monkeypatch.setattr(
        document_service, "embed_texts", lambda chunks: [[0.1], [0.2]]
    )
    insert = MagicMock()
    monkeypatch.setattr(document_service, "insert_chunks", insert)

    doc = document_service.create_and_process(db, "a.txt", b"hello")

    assert doc.status == "ready"
    assert doc.chunk_count == 2
    assert doc.error == ""
    insert.assert_called_once()


def test_create_and_process_parse_failure(monkeypatch, tmp_path):
    """解析失败时应标记 failed 并记录错误信息，而非抛出异常。"""
    db = _db()
    monkeypatch.setattr(document_service, "settings", SimpleNamespace(upload_abs=str(tmp_path)))

    def _boom(path, filename):
        raise ValueError("解析失败")

    monkeypatch.setattr(document_service, "parse_content", _boom)

    doc = document_service.create_and_process(db, "x.pdf", b"bad")

    assert doc.status == "failed"
    assert "解析失败" in doc.error


def test_remove_document(monkeypatch, tmp_path):
    """删除文档应清理向量、删除记录并提交事务。"""
    db = MagicMock()
    monkeypatch.setattr(document_service, "settings", SimpleNamespace(upload_abs=str(tmp_path)))

    delete = MagicMock()
    monkeypatch.setattr(document_service, "delete_doc", delete)

    doc = SimpleNamespace(id=5, filename="a.txt")
    document_service.remove_document(db, doc)

    delete.assert_called_once_with(5)
    db.delete.assert_called_once_with(doc)
    db.commit.assert_called_once()


def test_remove_document_unlink_missing_file_is_safe(monkeypatch, tmp_path):
    """本地文件不存在时 unlink 使用 missing_ok=True，不应报错。"""
    db = MagicMock()
    monkeypatch.setattr(document_service, "settings", SimpleNamespace(upload_abs=str(tmp_path)))
    monkeypatch.setattr(document_service, "delete_doc", MagicMock())

    doc = SimpleNamespace(id=999, filename="不存在.txt")
    document_service.remove_document(db, doc)  # 不应抛出异常