from uuid import uuid4

from app.security import create_user, issue_access_token


def cookie_headers(prefix: str) -> dict[str, str]:
    user_id = create_user(f"{prefix}-{uuid4().hex[:12]}", "test-password-123")
    return {"Cookie": f"access_token={issue_access_token(user_id)}"}
