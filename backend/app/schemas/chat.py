"""问答相关 Pydantic 模型。"""
from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    conversation_id: int | None = None


class SourceOut(BaseModel):
    doc_id: int
    filename: str
    text: str
    score: float


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    cached: bool
    created_at: str
    sources: list[SourceOut] = []

    @classmethod
    def from_message(cls, m, sources: list[SourceOut]) -> "MessageOut":
        return cls(
            id=m.id,
            role=m.role,
            content=m.content,
            cached=m.cached,
            created_at=m.created_at.strftime("%Y-%m-%d %H:%M") if m.created_at else "",
            sources=sources,
        )


class ConversationOut(BaseModel):
    id: int
    title: str
    created_at: str
    updated_at: str

    @classmethod
    def from_conversation(cls, c) -> "ConversationOut":
        return cls(
            id=c.id,
            title=c.title,
            created_at=c.created_at.strftime("%Y-%m-%d %H:%M") if c.created_at else "",
            updated_at=c.updated_at.strftime("%Y-%m-%d %H:%M") if c.updated_at else "",
        )