import logging

from fastapi import APIRouter, HTTPException
from app.schemas.query import QueryRequest, QueryResponse
from app.services.agent_service import AgentService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/query", response_model=QueryResponse)
async def query(req: QueryRequest):
    """Handle user query and orchestrate analysis."""
    try:
        agent = AgentService()
        result = await agent.handle_query(req.session_id, req.query, req.dataset_id)
        return QueryResponse(**result)
    except Exception:
        logger.exception("Query request failed for session %s", req.session_id)
        raise HTTPException(status_code=500, detail="Query processing failed")
