"""使用统计 Pydantic 模型。"""
from pydantic import BaseModel


class StatsOut(BaseModel):
    """仪表盘概览数据：各类计数与缓存命中率。"""

    document_count: int
    user_count: int
    conversation_count: int
    message_count: int
    cached_count: int
    cache_hit_rate: float