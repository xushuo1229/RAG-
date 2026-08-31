"""测试 app/core/security.py：密码哈希 + JWT 签发与校验。"""
import types

import jwt
import pytest
from fastapi import HTTPException

from app.core import security
from app.core.config import settings


def test_hash_and_verify_roundtrip():
    """密码加密后能通过校验，且密文不等于原文。"""
    hashed = security.hash_password("123456")
    assert hashed != "123456"
    assert security.verify_password("123456", hashed) is True


def test_verify_wrong_password():
    """错误密码应返回 False。"""
    hashed = security.hash_password("correct")
    assert security.verify_password("wrong", hashed) is False


def test_verify_invalid_hash_returns_false():
    """传入非法哈希串不应抛异常，而是返回 False。"""
    assert security.verify_password("123456", "not-a-bcrypt-hash") is False


def test_create_access_token_payload():
    """JWT 中应包含用户 id（字符串）、用户名和角色。"""
    user = types.SimpleNamespace(id=7, username="alice", role="user")
    token = security.create_access_token(user)
    payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    assert payload["sub"] == "7"
    assert payload["username"] == "alice"
    assert payload["role"] == "user"


def test_decode_valid_token():
    """合法 token 能正确解码出用户信息。"""
    user = types.SimpleNamespace(id=1, username="admin", role="admin")
    token = security.create_access_token(user)
    payload = security._decode_token(token)
    assert payload["username"] == "admin"
    assert payload["role"] == "admin"


def test_decode_invalid_token_raises_401():
    """乱写的 token 应抛出 401 未授权异常。"""
    with pytest.raises(HTTPException) as exc:
        security._decode_token("this.is.not.a.valid.token")
    assert exc.value.status_code == 401