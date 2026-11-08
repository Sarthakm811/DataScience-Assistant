from __future__ import annotations

from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from app.security import (
    authenticate_user,
    create_user,
    issue_access_token,
    require_auth,
)
from app.utils.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])


class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=128, pattern=r"^[A-Za-z0-9._-]+$")
    password: str = Field(min_length=8, max_length=256)


def _set_auth_cookie(response: Response, user_id: str) -> None:
    response.set_cookie(
        "access_token",
        issue_access_token(user_id),
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
        max_age=settings.access_token_expire_minutes * 60,
    )


@router.post("/register")
def register(credentials: Credentials, response: Response) -> Dict[str, str]:
    try:
        user_id = create_user(credentials.username, credentials.password)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    _set_auth_cookie(response, user_id)
    return {"user_id": user_id, "username": credentials.username}


@router.post("/login")
def login(credentials: Credentials, response: Response) -> Dict[str, str]:
    user_id = authenticate_user(credentials.username, credentials.password)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    _set_auth_cookie(response, user_id)
    return {"user_id": user_id, "username": credentials.username}


@router.post("/logout")
def logout(response: Response) -> Dict[str, bool]:
    response.delete_cookie("access_token")
    return {"success": True}


@router.get("/me")
def me(user_id: str = Depends(require_auth)) -> Dict[str, str]:
    return {"user_id": user_id}
