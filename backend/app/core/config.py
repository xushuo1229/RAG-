"""全局配置：从 .env 读取，集中管理所有外部依赖参数。"""
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# 向量维度：Milvus 建索引与 embedding 请求共用，保持单一来源，避免两处不一致
EMBED_DIM = 1024


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 阿里云百炼
    dashscope_api_key: str = ""
    llm_base_url: str = ""
    llm_model: str = "qwen-plus"
    embedding_model: str = "text-embedding-v4"
    dashscope_base_url: str = ""
    rerank_model: str = "gte-rerank-v2"

    # 存储
    milvus_db_path: str = "./data/milvus.db"
    sqlite_path: str = "./data/app.db"
    upload_dir: str = "./data/uploads"

    # 管理员预置账号
    admin_username: str = "admin"
    admin_password: str = "123456"

    # 应用
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    jwt_secret: str = "change-me"

    @property
    def milvus_db_abs(self) -> str:
        p = Path(self.milvus_db_path)
        return str(p if p.is_absolute() else (BASE_DIR / "data" / p.name))

    @property
    def sqlite_abs(self) -> str:
        p = Path(self.sqlite_path)
        return str(p if p.is_absolute() else (BASE_DIR / "data" / p.name))

    @property
    def upload_abs(self) -> str:
        p = Path(self.upload_dir)
        return str(p if p.is_absolute() else (BASE_DIR / "data" / "uploads"))

    @model_validator(mode="after")
    def _check_jwt_secret(self) -> "Settings":
        # 安全红线：禁止用占位/过短密钥启动，防止 token 被轻易伪造
        if not self.jwt_secret or self.jwt_secret == "change-me" or len(self.jwt_secret) < 32:
            raise ValueError(
                "JWT_SECRET 不满足安全要求：请在 backend/.env 中配置至少 32 位的随机密钥"
            )
        return self


settings = Settings()
