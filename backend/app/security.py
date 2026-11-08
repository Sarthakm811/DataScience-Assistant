from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, Optional
from uuid import uuid4

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from fastapi import Cookie, Depends, HTTPException

from app.runtime_state import set_current_tenant
from app.utils.config import settings

_PASSWORDS = PasswordHasher()
_USERS: Dict[str, Dict[str, str]] = {}
_USERNAME_TO_ID: Dict[str, str] = {}
_COOKIE_NAME = "access_token"


def create_user(username: str, password: str) -> str:
    normalized = username.casefold()
    if normalized in _USERNAME_TO_ID:
        raise ValueError("Username is already registered")
    user_id = str(uuid4())
    _USERS[user_id] = {
        "username": username,
        "password_hash": _PASSWORDS.hash(password),
    }
    _USERNAME_TO_ID[normalized] = user_id
    return user_id


def authenticate_user(username: str, password: str) -> Optional[str]:
    user_id = _USERNAME_TO_ID.get(username.casefold())
    if user_id is None:
        return None
    try:
        _PASSWORDS.verify(_USERS[user_id]["password_hash"], password)
    except (InvalidHashError, VerificationError, VerifyMismatchError):
        return None
    return user_id


def issue_access_token(user_id: str) -> str:
    expires = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    return jwt.encode(
        {"sub": user_id, "exp": expires},
        settings.secret_key,
        algorithm="HS256",
    )


def require_auth(access_token: str | None = Cookie(default=None)) -> str:
    if not access_token:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        payload = jwt.decode(access_token, settings.secret_key, algorithms=["HS256"])
        user_id = payload.get("sub")
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc
    if not isinstance(user_id, str) or user_id not in _USERS:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user_id


async def bind_tenant_context(user_id: str = Depends(require_auth)):
    """Bind the tenant to the authenticated user; client headers are ignored."""
    set_current_tenant(user_id)
