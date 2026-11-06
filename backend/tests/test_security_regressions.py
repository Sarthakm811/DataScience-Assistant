import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.runtime_state import set_current_tenant
from app.services.session_store import SessionStore
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
        "X-Tenant-Id": "regression-tenant",
    }


@pytest.mark.asyncio
async def test_specialized_routes_require_authentication(client):
    response = await client.post("/api/sessions", json={})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_health_remains_public(client):
    response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_upload_enforces_server_size_limit(client, auth_headers, monkeypatch):
    monkeypatch.setattr(settings, "max_upload_size_mb", 1)
    response = await client.post(
        "/api/datasets/upload",
        headers=auth_headers,
        files={"file": ("large.csv", b"a" * (1024 * 1024 + 1), "text/csv")},
    )
    assert response.status_code == 413


@pytest.mark.asyncio
async def test_upload_rejects_malformed_csv(client, auth_headers):
    response = await client.post(
        "/api/datasets/upload",
        headers=auth_headers,
        files={"file": ("broken.csv", b"\xff\xfe\x00\x00", "text/csv")},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid CSV file"


@pytest.mark.asyncio
async def test_query_rejects_empty_payload(client, auth_headers):
    response = await client.post(
        "/api/query",
        headers=auth_headers,
        json={"session_id": "", "query": ""},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_mcp_call_does_not_report_fake_success(client, auth_headers):
    response = await client.post(
        "/api/v1/tools/analyzer.eda/call",
        headers=auth_headers,
        json={"inputs": {"dataset_path": "data.csv"}},
    )
    assert response.status_code == 501


def test_session_store_is_tenant_scoped():
    store = SessionStore()
    set_current_tenant("tenant-a")
    store.set_session("shared-id", {"owner": "tenant-a"})

    set_current_tenant("tenant-b")
    assert store.get_session("shared-id") is None

    set_current_tenant("tenant-a")
    assert store.get_session("shared-id") == {"owner": "tenant-a"}


def test_feature_dataset_headers_must_be_unique():
    from app.api.runtime_compat import FeatureEngineeringSaveRequest

    with pytest.raises(ValueError, match="must be unique"):
        FeatureEngineeringSaveRequest(
            headers=["value", "value"],
            rows=[{"value": 1}],
        )


@pytest.mark.asyncio
async def test_execution_requires_sandbox_confirmation(monkeypatch):
    from app.tools.execution_tool import ExecutionTool

    monkeypatch.setattr(settings, "allow_code_execution", True)
    monkeypatch.delenv("EXECUTION_SANDBOX_CONFIRMED", raising=False)

    result = await ExecutionTool().execute("print('unsafe')", job_id="test-job")
    assert result["status"] == "disabled"
    assert "isolated sandbox" in result["error"]
