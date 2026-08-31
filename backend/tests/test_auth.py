"""测试 app/api/auth.py：用户注册 / 登录 / 改密 / 当前用户。"""
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.api import auth
from app.core.security import hash_password
from app.schemas.user import ChangePasswordRequest, LoginRequest, RegisterRequest


def _user(id=1, username="alice", role="user", password="123456"):
    """构造一个带已哈希密码的用户对象，避免真实数据库。"""
    return SimpleNamespace(
        id=id,
        username=username,
        role=role,
        password_hash=hash_password(password),
        created_at=None,
    )


# ---- 注册 ----
def test_register_success():
    db = MagicMock()
    db.scalar.return_value = None  # 用户名不存在
    result = auth.register(RegisterRequest(username="alice", password="123456"), db=db)
    assert result.message == "注册成功，请登录"
    db.add.assert_called_once()
    db.commit.assert_called_once()


def test_register_duplicate_username():
    db = MagicMock()
    db.scalar.return_value = object()  # 用户名已存在
    with pytest.raises(HTTPException) as exc:
        auth.register(RegisterRequest(username="alice", password="123456"), db=db)
    assert exc.value.status_code == 409


# ---- 登录 ----
def test_login_success():
    db = MagicMock()
    db.scalar.return_value = _user(username="alice", role="user")
    result = auth.login(LoginRequest(username="alice", password="123456"), db=db)
    assert result.username == "alice"
    assert result.role == "user"
    assert result.access_token  # 应返回非空 token


def test_login_wrong_password():
    db = MagicMock()
    db.scalar.return_value = _user(password="correct")
    with pytest.raises(HTTPException) as exc:
        auth.login(LoginRequest(username="alice", password="wrong"), db=db)
    assert exc.value.status_code == 401


def test_login_user_not_found():
    db = MagicMock()
    db.scalar.return_value = None
    with pytest.raises(HTTPException) as exc:
        auth.login(LoginRequest(username="ghost", password="123456"), db=db)
    assert exc.value.status_code == 401


# ---- 改密 ----
def test_change_password_success():
    db = MagicMock()
    user = _user(password="oldpass123")
    result = auth.change_password(
        ChangePasswordRequest(old_password="oldpass123", new_password="newpass456"),
        user=user,
        db=db,
    )
    assert result.message == "密码修改成功，请重新登录"
    db.commit.assert_called_once()


def test_change_password_wrong_old():
    db = MagicMock()
    user = _user(password="correct")
    with pytest.raises(HTTPException) as exc:
        auth.change_password(
            ChangePasswordRequest(old_password="wrong", new_password="newpass456"),
            user=user,
            db=db,
        )
    assert exc.value.status_code == 400


# ---- 当前用户 ----
def test_me():
    user = _user(username="alice", role="user")
    result = auth.me(user=user)
    assert result.username == "alice"
    assert result.role == "user"