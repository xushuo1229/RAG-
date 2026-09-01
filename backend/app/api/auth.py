"""认证与用户管理路由。"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    create_access_token,
    get_current_user,
    hash_password,
    require_admin,
    verify_password,
)
from app.models.user import User
from app.schemas.user import (
    ChangePasswordRequest,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    TokenResponse,
    UserOut,
)

router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/register", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, db: Annotated[Session, Depends(get_db)]):
    """注册新用户；用户名重复返回 409，密码用 bcrypt 加密后入库。"""
    if db.scalar(select(User).where(User.username == body.username)):
        raise HTTPException(status.HTTP_409_CONFLICT, "用户名已被注册")
    db.add(User(username=body.username, password_hash=hash_password(body.password)))
    db.commit()
    return MessageResponse(message="注册成功，请登录")


@router.get("/check-username")
def check_username(username: str, db: Annotated[Session, Depends(get_db)]):
    """检查用户名是否已被占用，供注册页实时查重。"""
    exists = db.scalar(select(User).where(User.username == username)) is not None
    return {"username": username, "exists": exists}


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Annotated[Session, Depends(get_db)]):
    """校验用户名密码，通过则签发 JWT 并返回用户角色。"""
    user = db.scalar(select(User).where(User.username == body.username))
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "用户名或密码错误")
    return TokenResponse(
        access_token=create_access_token(user),
        username=user.username,
        role=user.role,
    )


@router.get("/me", response_model=UserOut)
def me(user: Annotated[User, Depends(get_current_user)]):
    """返回当前登录用户的资料。"""
    return UserOut.from_user(user)


@router.put("/password", response_model=MessageResponse)
def change_password(
    body: ChangePasswordRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """修改当前用户密码：先校验原密码，再用 bcrypt 重新哈希新密码。"""
    if not verify_password(body.old_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "原密码错误")
    user.password_hash = hash_password(body.new_password)
    db.commit()
    return MessageResponse(message="密码修改成功，请重新登录")


@router.get("/users", response_model=list[UserOut])
def list_users(
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    """用户列表（仅管理员）。"""
    return [UserOut.from_user(u) for u in db.scalars(select(User).order_by(User.id)).all()]
