"""LangChain-powered query endpoint (optional — gracefully disabled if deps are missing)."""

from fastapi import APIRouter, HTTPException
import uuid
import logging

from app.schemas.query import QueryRequest, QueryResponse
from app.runtime_state import DATASETS
from app.services.dataset_context import format_dataframe_context

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/query/langchain", response_model=QueryResponse)
async def query_with_langchain(req: QueryRequest):
    """Handle query using LangChain multi-tool orchestration."""
    job_id = str(uuid.uuid4())
    try:
        # Lazy import so a version mismatch doesn't crash the whole server at startup
        try:
            from app.services.langchain_agent import LangChainAgent
        except Exception:
            logger.exception("LangChain agent import failed")
            raise HTTPException(
                status_code=503,
                detail="LangChain agent is unavailable",
            )

        agent = LangChainAgent()
        context = {"dataset_id": req.dataset_id} if req.dataset_id else {}
        if req.dataset_id and req.dataset_id in DATASETS:
            context["dataset_context"] = format_dataframe_context(
                DATASETS[req.dataset_id]
            )
        result = await agent.run(req.query, context)

        return QueryResponse(
            job_id=job_id,
            status=result.get("status", "completed"),
            explanation=result.get("output", ""),
            error=result.get("error"),
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("LangChain query failed for session %s", req.session_id)
        raise HTTPException(status_code=500, detail="LangChain query processing failed")
