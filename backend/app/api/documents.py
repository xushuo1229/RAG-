"""知识库文档管理路由（仅管理员）。"""
import asyncio
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_admin
from app.models.document import Document
from app.models.user import User
from app.schemas.document import DocumentListResponse, DocumentOut
from app.schemas.user import MessageResponse
from app.services.document_service import create_and_process, remove_document
from app.services.loader import SUPPORTED

router = APIRouter(prefix="/api/documents", tags=["知识库"])


@router.get("", response_model=DocumentListResponse)
def list_documents(
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
    search: str = Query(default="", description="按文件名模糊搜索"),
    page: int = Query(default=1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(default=10, ge=1, le=100, description="每页条数"),
):
    """返回知识库文档分页列表（仅管理员），支持按文件名搜索，按创建时间倒序。"""
    filters = []
    if search:
        filters.append(Document.filename.contains(search))

    total = db.scalar(select(func.count()).select_from(Document).where(*filters)) or 0
    docs = db.scalars(
        select(Document)
        .where(*filters)
        .order_by(Document.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return DocumentListResponse(
        total=total,
        items=[DocumentOut.from_doc(d) for d in docs],
    )


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
    file: UploadFile = File(...),
):
    """上传文档并触发入库流水线；只校验扩展名，路径用 basename 防目录穿越。"""
    filename = Path(file.filename or "").name
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in SUPPORTED:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"仅支持上传：{', '.join(sorted(SUPPORTED))}")
    content = await file.read()
    if not content:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "文件内容为空")
    # 解析/切分/向量化含多次同步外部 HTTP 调用，放到线程池执行，避免阻塞事件循环
    doc = await asyncio.to_thread(create_and_process, db, filename, content)
    return DocumentOut.from_doc(doc)


@router.delete("/{doc_id}", response_model=MessageResponse)
def delete_document(
    doc_id: int,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    """删除指定文档：清理向量库、关系库记录与本地文件（仅管理员）。"""
    doc = db.get(Document, doc_id)
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "文档不存在")
    remove_document(db, doc)
    return MessageResponse(message="文档已删除")