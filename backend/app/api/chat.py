"""多会话管理与 RAG 问答路由（SSE 流式）。"""
import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, get_db
from app.core.milvus import cache_insert, cache_lookup, recommend_questions
from app.core.rate_limit import question_limiter
from app.core.security import get_current_user
from app.models.chat import Conversation, Message
from app.models.document import Document
from app.models.user import User
from app.schemas.chat import AskRequest, ConversationOut, MessageOut, SourceOut
from app.schemas.user import MessageResponse
from app.services.embedding import embed_query
from app.services.llm import build_messages, stream_chat
from app.services.rag_service import SYSTEM_PROMPT, build_prompt, retrieve

router = APIRouter(prefix="/api", tags=["问答"])

# 会话标题最大长度：取问题前 N 个字符作为标题
TITLE_MAX_LEN = 50


def _sse(type_: str, data) -> str:
    return f"data: {json.dumps({'type': type_, 'data': data}, ensure_ascii=False)}\n\n"


# ---------------- 会话管理 ----------------


@router.get("/conversations", response_model=list[ConversationOut])
def list_conversations(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """返回当前用户的所有会话，按最近更新时间倒序。"""
    convs = db.scalars(
        select(Conversation).where(Conversation.user_id == user.id).order_by(Conversation.updated_at.desc())
    ).all()
    return [ConversationOut.from_conversation(c) for c in convs]


@router.get("/conversations/{conv_id}/messages", response_model=list[MessageOut])
def list_messages(
    conv_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """返回某个会话的全部消息；不属于当前用户的会话返回 404。"""
    conv = db.get(Conversation, conv_id)
    if conv is None or conv.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "会话不存在")
    msgs = db.scalars(
        select(Message).where(Message.conversation_id == conv_id).order_by(Message.id)
    ).all()
    return [_message_out(m) for m in msgs]


@router.delete("/conversations/{conv_id}", response_model=MessageResponse)
def delete_conversation(
    conv_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """删除指定会话及其下所有消息；仅允许删除自己的会话。"""
    conv = db.get(Conversation, conv_id)
    if conv is None or conv.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "会话不存在")
    for m in db.scalars(select(Message).where(Message.conversation_id == conv_id)).all():
        db.delete(m)
    db.delete(conv)
    db.commit()
    return MessageResponse(message="会话已删除")


# ---------------- 问答（SSE） ----------------


def _message_out(m: Message) -> MessageOut:
    """把消息记录转换为响应模型，并解析其中的引用来源 JSON。"""
    try:
        sources = [SourceOut(**s) for s in json.loads(m.sources or "[]")]
    except (json.JSONDecodeError, TypeError):
        sources = []
    return MessageOut.from_message(m, sources)


@router.post("/chat")
def chat(
    body: AskRequest,
    user: Annotated[User, Depends(get_current_user)],
):
    """RAG 问答入口：以 SSE 流式返回引用来源与回答增量，含限流与语义缓存。"""
    question = body.question.strip()
    if not question:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "问题不能为空")
    if not question_limiter.allow(str(user.id)):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "提问过于频繁，请稍后再试")

    def event_stream():
        """SSE 生成器：串起 建会话→历史→存问题→查询缓存→检索→流式生成→存回答。

        数据库连接只在三个短事务中短暂持有（建会话/存缓存命中/存回答），
        LLM 流式生成等慢 I/O 期间不占连接，避免高并发下连接池耗尽。
        """
        # ---- 阶段 1：短事务——确定会话 / 读历史 / 存用户消息 ----
        with SessionLocal() as db:
            conv = None
            if body.conversation_id:
                conv = db.get(Conversation, body.conversation_id)
                if conv is None or conv.user_id != user.id:
                    yield _sse("error", "会话不存在")
                    return
            else:
                conv = Conversation(user_id=user.id, title=question[:TITLE_MAX_LEN])
                db.add(conv)
                db.commit()
                db.refresh(conv)
            conversation_id = conv.id

            history = [
                {"role": m.role, "content": m.content}
                for m in db.scalars(
                    select(Message).where(Message.conversation_id == conv.id).order_by(Message.id)
                ).all()
            ]

            db.add(Message(conversation_id=conv.id, role="user", content=question))
            db.commit()

            doc_name_map = {d.id: d.filename for d in db.scalars(select(Document)).all()}

        # ---- 阶段 2：慢 I/O（向量化/缓存/检索/LLM 流式），不占数据库连接 ----
        q_embedding = embed_query(question)
        cached_answer = cache_lookup(q_embedding)
        if cached_answer:
            yield _sse("sources", [])
            yield _sse("delta", cached_answer)
            with SessionLocal() as db:
                db.add(
                    Message(
                        conversation_id=conversation_id,
                        role="assistant",
                        content=cached_answer,
                        cached=True,
                        sources="[]",
                    )
                )
                db.commit()
            yield _sse("done", {"conversation_id": conversation_id, "cached": True})
            return

        try:
            sources, context = retrieve(question, doc_name_map)
        except Exception:  # noqa: BLE001 不把内部细节（路径/traceback）暴露给前端
            yield _sse("error", "检索失败，请稍后重试")
            return
        yield _sse("sources", [s.model_dump() for s in sources])

        messages = build_messages(SYSTEM_PROMPT, history, build_prompt(context, question))
        parts: list[str] = []
        for delta in stream_chat(messages):
            parts.append(delta)
            yield _sse("delta", delta)
        answer = "".join(parts)

        # 相似问题推荐：写缓存之前检索相近历史提问，避免匹配到本次问题本身
        related = recommend_questions(q_embedding)
        if related:
            yield _sse("related", related)

        # ---- 阶段 3：短事务——保存回答 ----
        with SessionLocal() as db:
            db.add(
                Message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=answer,
                    sources=json.dumps([s.model_dump() for s in sources], ensure_ascii=False),
                )
            )
            conv = db.get(Conversation, conversation_id)
            if conv is not None:
                conv.title = conv.title or question[:TITLE_MAX_LEN]
            db.commit()
        if answer:
            cache_insert(question, answer, q_embedding)
        yield _sse("done", {"conversation_id": conversation_id, "cached": False})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )