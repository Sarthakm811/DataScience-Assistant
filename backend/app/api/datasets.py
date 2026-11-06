import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.tools.kaggle_tool import KaggleTool
from app.runtime_state import get_current_tenant
from app.utils.reliability import InFlightOperationGuard, retry_async

router = APIRouter()
kaggle_tool = KaggleTool()
logger = logging.getLogger(__name__)
search_guard = InFlightOperationGuard()


class DatasetSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    page: int = Field(default=1, ge=1, le=1000)
    limit: int = Field(default=10, ge=1, le=100)


@router.post("/datasets/search")
async def search_datasets(req: DatasetSearchRequest):
    """Search Kaggle datasets."""
    operation_key = f"{get_current_tenant()}:{req.query.casefold()}:{req.page}"
    with search_guard.hold(operation_key):
        try:
            results = await retry_async(
                lambda: kaggle_tool.search_datasets(req.query, req.page),
                attempts=2,
                logger=logger,
                operation_name="Kaggle dataset search",
            )
            return {"datasets": results}
        except HTTPException:
            raise
        except Exception as exc:
            logger.error(
                "Dataset search failed: error_type=%s query_length=%s page=%s",
                type(exc).__name__,
                len(req.query),
                req.page,
            )
            raise HTTPException(
                status_code=502,
                detail="Dataset search is temporarily unavailable",
            ) from exc
