# API Documentation

## Base URLs

The FastAPI application exposes:

```text
http://localhost:8000
```

Application endpoints are prefixed with `/api`. There is no `/api/v1` prefix
in the current implementation.

## Authentication

All `/api/*` endpoints require:

```http
X-API-Key: <configured API key>
X-Tenant-Id: <tenant identifier>
```

The API key is configured by the backend `SECRET_KEY` setting. The tenant
header is required when `ENFORCE_TENANT_ISOLATION=true`, which is the
production default.

The following endpoints are public:

```http
GET /
GET /health
```

Do not expose `SECRET_KEY` or backend credentials in frontend source. A
browser-embedded `VITE_API_KEY` must be treated as a client credential, not a
secret.

## Common errors

```json
{
  "detail": "Error message"
}
```

- `400`: Invalid request or missing tenant header
- `401`: Missing or invalid API key
- `404`: Dataset, model, session, or tool not found
- `413`: Upload or dataset exceeds configured limits
- `501`: Feature is not configured, such as MCP task execution
- `502`: External dataset provider is unavailable
- `503`: Optional service or dependency is unavailable

## Sessions

### Create session

```http
POST /api/sessions
Content-Type: application/json
X-API-Key: <api-key>
X-Tenant-Id: <tenant-id>
```

Request:

```json
{
  "user_id": "optional-user-id"
}
```

Response:

```json
{
  "session_id": "uuid",
  "created_at": "2026-11-03T00:00:00",
  "last_activity": "2026-11-03T00:00:00"
}
```

### Get session history

```http
GET /api/sessions/{session_id}/history
```

Response:

```json
{
  "history": [
    {
      "query": "User query",
      "response": "Agent response",
      "job_id": "uuid"
    }
  ]
}
```

Session state is tenant-scoped. The same session ID cannot be used to read
another tenant's session data.

## Queries

### Submit query

```http
POST /api/query
Content-Type: application/json
```

Request:

```json
{
  "session_id": "uuid",
  "query": "Show me summary statistics",
  "dataset_id": "optional-live-dataset-id"
}
```

### Submit enhanced query

```http
POST /api/query/enhanced
```

Request:

```json
{
  "session_id": "uuid",
  "query": "Summarize this dataset",
  "dataset_id": "ds_example",
  "auto_eda": true,
  "auto_ml": false,
  "target_column": null
}
```

### Submit LangChain query

```http
POST /api/query/langchain
```

The LangChain integration is optional and returns `503` when its dependencies
are unavailable.

## Dataset management

### Upload dataset

```http
POST /api/datasets/upload
Content-Type: multipart/form-data
```

Supported formats are CSV, XLS/XLSX, JPG, JPEG, and PNG. The backend enforces
server-side limits:

- Maximum file size: 50 MB
- Maximum rows: 1,000,000
- Maximum columns: 500
- Maximum image pixels: 25,000,000

The upload endpoint returns `413` when a configured limit is exceeded.

### List datasets

```http
GET /api/datasets
```

### Get dataset preview

```http
GET /api/datasets/{dataset_id}/preview?rows=10
```

### Download dataset

```http
GET /api/datasets/{dataset_id}/download?format=csv
```

Supported download formats are `csv` and `json`.

### Delete dataset

```http
DELETE /api/datasets/{dataset_id}
```

### Search Kaggle datasets

```http
POST /api/datasets/search
Content-Type: application/json
```

Request:

```json
{
  "query": "housing",
  "page": 1,
  "limit": 10
}
```

The endpoint requires valid Kaggle credentials configured on the backend.

## Analysis and machine learning

Important endpoints include:

```http
POST /api/eda/analyze?dataset_id=<id>
POST /api/eda/statistical-tests?dataset_id=<id>&column1=<name>
POST /api/ml/train
POST /api/ml/train-selected
POST /api/ml/cluster
POST /api/predict
POST /api/explain/shap
POST /api/explain/feature-importance
POST /api/statistics-math/analyze
```

ML and statistical request models validate expensive parameters such as trial
counts, cross-validation folds, cluster counts, confidence levels, and
forecast horizons before running computation.

## Reports and chat

```http
POST /api/report/generate?dataset_id=<id>&type=pdf
GET /api/reports/history/{session_id}
POST /api/chat
GET /api/chat/history/{session_id}
```

## MCP tools

Tool discovery and validation endpoints are under:

```http
GET /api/v1/tools/
GET /api/v1/tools/{tool_id}
POST /api/v1/tools/{tool_id}/validate
```

Tool execution currently returns `501 Not Implemented` because the task queue
and executor publication path is not configured. It does not report a fake
queued task.

## Code execution policy

Code execution is disabled by default. Enabling it requires both:

```env
ALLOW_CODE_EXECUTION=true
EXECUTION_SANDBOX_CONFIRMED=true
```

The confirmation flag is only appropriate when the executor is deployed with
independent OS/container isolation, network restrictions, CPU and memory
limits, and an explicit filesystem policy.
