import pandas as pd
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.db import database
from app.main import app
from app.runtime_state import DATASETS, set_current_tenant
from app.utils.config import settings


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def auth_headers():
    return {
        "X-API-Key": settings.secret_key,
        "X-Tenant-Id": "resilience-tenant",
    }


@pytest.mark.asyncio
async def test_dataset_search_rejects_invalid_pagination(client, auth_headers):
    response = await client.post(
        "/api/datasets/search",
        headers=auth_headers,
        json={"query": "weather", "page": 0, "limit": 101},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_dataset_search_maps_network_failure(client, auth_headers, monkeypatch):
    async def unavailable(*args, **kwargs):
        raise ConnectionError("provider unavailable")

    monkeypatch.setattr("app.api.datasets.kaggle_tool.search_datasets", unavailable)
    response = await client.post(
        "/api/datasets/search",
        headers=auth_headers,
        json={"query": "weather"},
    )
    assert response.status_code == 502
    assert response.json()["detail"] == "Dataset search is temporarily unavailable"


@pytest.mark.asyncio
async def test_duplicate_uploads_receive_distinct_ids(client, auth_headers):
    content = b"name,value\none,1\ntwo,2\n"
    first = await client.post(
        "/api/datasets/upload",
        headers=auth_headers,
        files={"file": ("duplicate.csv", content, "text/csv")},
    )
    second = await client.post(
        "/api/datasets/upload",
        headers=auth_headers,
        files={"file": ("duplicate.csv", content, "text/csv")},
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] != second.json()["id"]


@pytest.mark.asyncio
async def test_missing_dataset_returns_not_found(client, auth_headers):
    response = await client.get(
        "/api/datasets/does-not-exist",
        headers=auth_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_missing_session_history_is_empty(client, auth_headers):
    response = await client.get(
        "/api/sessions/missing-session/history",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json() == {"history": []}


@pytest.mark.asyncio
async def test_unexpected_query_failure_returns_request_id(client, auth_headers, monkeypatch):
    class BrokenAgent:
        async def handle_query(self, *args, **kwargs):
            raise RuntimeError("internal provider detail")

    monkeypatch.setattr("app.api.query.AgentService", BrokenAgent)
    response = await client.post(
        "/api/query",
        headers=auth_headers,
        json={"session_id": "s1", "query": "hello"},
    )
    assert response.status_code == 500
    assert response.json()["detail"] == "Query processing failed"
    assert response.headers["X-Request-Id"]
    assert "internal provider detail" not in response.text


def test_database_unconfigured_failure_is_explicit(monkeypatch):
    monkeypatch.setattr(database, "SessionLocal", None)
    monkeypatch.setattr(settings, "database_url", None)
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        next(database.get_db())


def test_database_session_is_closed_after_use(monkeypatch):
    closed = []

    class FakeSession:
        def close(self):
            closed.append(True)

    monkeypatch.setattr(database, "SessionLocal", lambda: FakeSession())
    generator = database.get_db()
    assert next(generator).__class__ is FakeSession
    with pytest.raises(StopIteration):
        next(generator)
    assert closed == [True]


def test_session_state_isolated_after_tenant_switch():
    set_current_tenant("resilience-a")
    DATASETS["same-id"] = pd.DataFrame({"value": [1]})
    set_current_tenant("resilience-b")
    assert "same-id" not in DATASETS
