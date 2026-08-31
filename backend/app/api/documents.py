"""知识库文档管理路由（仅管理员）。"""
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_admin
from app.models.document import Document
from app.models.user import User
from app.schemas.document import DocumentOut
from app.schemas.user import MessageResponse
from app.services.document_service import create_and_process, remove_document
from app.services.loader import SUPPORTED

router = APIRouter(prefix="/api/documents", tags=["知识库"])


@router.get("", response_model=list[DocumentOut])
def list_documents(
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    docs = db.scalars(select(Document).order_by(Document.id.desc())).all()
    return [DocumentOut.from_doc(d) for d in docs]


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
    file: UploadFile = File(...),
):
    filename = Path(file.filename or "").name
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in SUPPORTED:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"仅支持上传：{', '.join(sorted(SUPPORTED))}")
    content = await file.read()
    if not content:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "文件内容为空")
    doc = create_and_process(db, filename, content)
    return DocumentOut.from_doc(doc)


@router.delete("/{doc_id}", response_model=MessageResponse)
def delete_document(
    doc_id: int,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    doc = db.get(Document, doc_id)
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "文档不存在")
    remove_document(db, doc)
    return MessageResponse(message="文档已删除")