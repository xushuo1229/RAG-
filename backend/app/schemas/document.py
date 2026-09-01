"""知识库文档 Pydantic 模型。"""
from pydantic import BaseModel


class DocumentOut(BaseModel):
    id: int
    filename: str
    file_type: str
    size: int
    chunk_count: int
    status: str
    error: str
    created_at: str

    @classmethod
    def from_doc(cls, doc) -> "DocumentOut":
        return cls(
            id=doc.id,
            filename=doc.filename,
            file_type=doc.file_type,
            size=doc.size,
            chunk_count=doc.chunk_count,
            status=doc.status,
            error=doc.error or "",
            created_at=doc.created_at.strftime("%Y-%m-%d %H:%M") if doc.created_at else "",
        )


class DocumentListResponse(BaseModel):
    """文档分页列表响应：总数 + 当前页条目。"""

    total: int
    items: list[DocumentOut]