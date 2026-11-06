from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List


class QueryRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128, pattern=r"\S")
    query: str = Field(min_length=1, max_length=20_000, pattern=r"\S")
    dataset_id: Optional[str] = Field(default=None, max_length=255, pattern=r"\S")


class QueryResponse(BaseModel):
    job_id: str
    status: str
    plan: Optional[str] = None
    code: Optional[str] = None
    results: Optional[Dict[str, Any]] = None
    artifacts: Optional[List[str]] = None
    explanation: Optional[str] = None
    error: Optional[str] = None


class SessionCreate(BaseModel):
    user_id: Optional[str] = Field(default=None, max_length=255, pattern=r"\S")


class SessionResponse(BaseModel):
    session_id: str
    created_at: str
    last_activity: str
