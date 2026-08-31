"""测试 app/core/config.py：路径解析为绝对路径。"""
from app.core.config import BASE_DIR, settings


def test_sqlite_path_absolute():
    assert settings.sqlite_abs == str(BASE_DIR / "data" / "app.db")


def test_milvus_path_absolute():
    assert settings.milvus_db_abs == str(BASE_DIR / "data" / "milvus.db")


def test_upload_dir_absolute():
    assert settings.upload_abs == str(BASE_DIR / "data" / "uploads")