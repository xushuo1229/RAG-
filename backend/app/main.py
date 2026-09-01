"""FastAPI 应用入口。"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth_router, chat_router, documents_router, stats_router
from app.core.database import init_db
from app.core.milvus import init_collections


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    init_collections()
    yield


app = FastAPI(
    title="RAG 企业级知识库问答系统",
    description="基于 LangChain + Milvus + 阿里云百炼的电商商品知识库问答服务",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(documents_router)
app.include_router(chat_router)
app.include_router(stats_router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "app": "rag-knowledge-base", "version": "0.2.0"}
