"""使用统计路由（仅管理员）。"""
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_admin
from app.models.chat import Conversation, Message
from app.models.document import Document
from app.models.user import User
from app.schemas.stats import StatsOut

router = APIRouter(prefix="/api/stats", tags=["统计"])


@router.get("", response_model=StatsOut)
def get_stats(
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    """返回仪表盘概览：文档/用户/会话/消息数量与语义缓存命中率。"""
    document_count = db.scalar(select(func.count()).select_from(Document)) or 0
    user_count = db.scalar(select(func.count()).select_from(User)) or 0
    conversation_count = db.scalar(select(func.count()).select_from(Conversation)) or 0
    message_count = db.scalar(select(func.count()).select_from(Message)) or 0
    cached_count = (
        db.scalar(select(func.count()).select_from(Message).where(Message.cached.is_(True))) or 0
    )
    # 命中率分母取消息总数，无消息时置 0 避免除零
    cache_hit_rate = round(cached_count / message_count * 100, 1) if message_count else 0.0

    return StatsOut(
        document_count=document_count,
        user_count=user_count,
        conversation_count=conversation_count,
        message_count=message_count,
        cached_count=cached_count,
        cache_hit_rate=cache_hit_rate,
    )