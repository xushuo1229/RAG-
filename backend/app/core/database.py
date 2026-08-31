"""数据库会话管理：SQLAlchemy 2.x + SQLite（写法兼容 PostgreSQL）。"""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

engine = create_engine(
    f"sqlite:///{settings.sqlite_abs}",
    connect_args={"check_same_thread": False},
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """建表并预置管理员账号 admin/123456。"""
    import app.models  # noqa: F401 确保模型注册

    Base.metadata.create_all(engine)

    from app.core.security import hash_password
    from app.models.user import User

    with SessionLocal() as db:
        if db.query(User).filter_by(username=settings.admin_username).first() is None:
            db.add(
                User(
                    username=settings.admin_username,
                    password_hash=hash_password(settings.admin_password),
                    role="admin",
                )
            )
            db.commit()
