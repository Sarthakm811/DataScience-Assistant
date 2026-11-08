# DataScience Assistant

DataScience Assistant is a full-stack application for exploring datasets,
running exploratory data analysis, training machine-learning models, and
generating reports.

The project contains:

- A **FastAPI backend** in `backend/`
- A **React + Vite frontend** in `frontend/`
- Docker and deployment configuration for local and hosted environments
- Backend and frontend automated tests

The application is designed for interactive analysis. Runtime datasets,
trained models, preprocessors, sessions, and chat history are stored in memory.
They are isolated by authenticated user, but they are lost when the backend
restarts. This is not a replacement for a persistent data warehouse or model
registry.

## What the application can do

### Dataset workflows

- Upload CSV, XLSX, and supported image-based data files
- List, preview, download, and delete datasets
- Search Kaggle datasets and download a selected dataset when Kaggle
  credentials are supplied
- Clean missing values, duplicates, outliers, text, dates, and numeric formats
- Create engineered features and save the result as a new in-memory dataset
- Apply preprocessing options such as imputation, encoding, scaling, and feature
  selection

### Analysis workflows

- Generate automatic EDA summaries
- Inspect descriptive statistics, data types, missing values, outliers, and
  correlations
- Produce categorical, trend, segmentation, behavioral, and comparative
  insights
- Run statistical tests including t-tests, ANOVA, chi-square, and confidence
  intervals
- Run custom EDA statistical tests for one or two selected columns
- Generate JSON or PDF reports

### Machine learning workflows

- Train a selected model or compare multiple models
- Support classification, regression, multi-output, and clustering workflows
- Use leakage-safe sklearn pipelines with:
  - Numeric imputation
  - Categorical imputation
  - Scaling
  - One-hot encoding with unknown-category handling
- Use stratified train/test splits for classification when possible
- Optionally calculate cross-validation metrics and standard deviation
- Save the complete preprocessing and model pipeline for prediction
- Explain models with feature importance and SHAP when supported
- Detect available GPU capabilities without forcing GPU-only execution

### Query and assistant workflows

- Create and inspect analysis sessions
- Ask dataset-aware questions through standard, enhanced, and LangChain-backed
  query endpoints
- Use the chat interface to ask questions about the current dataset
- Integrate optional Gemini and Kaggle services when their credentials are
  configured

## Architecture

```text
frontend/
  React pages, components, context, API service, and Vitest tests

backend/
  app/
    main.py                 FastAPI application and router registration
    api/                    Authentication and API routers
    services/               Shared business services, including training
    runtime_state.py        Tenant-scoped in-memory runtime stores
    security.py             Password hashing, JWT cookies, and tenant binding
    eda_engine.py           EDA and statistical analysis
    ml_engine.py            Model and GPU support
    preprocessing.py        Data cleaning and preprocessing
  tests/                    Pytest test suite

docs/
  API and setup documentation

infra/
  Deployment manifests
```

The frontend communicates with the backend through `VITE_API_URL`. In local
development, the frontend normally runs on port `5173` and the backend on port
`8000`.

## Authentication and tenant isolation

Protected API endpoints use real accounts:

1. Register with a username and password.
2. The backend hashes the password with Argon2.
3. Login or registration sets a short-lived JWT in an HttpOnly cookie.
4. The backend derives the tenant ID from the authenticated user ID.
5. Client-supplied tenant headers cannot change the active tenant.

The browser never receives `SECRET_KEY`, an API key, or a tenant credential.
Frontend requests send cookies with `credentials: "include"`.

Public endpoints:

```text
GET /
GET /health
POST /api/auth/register
POST /api/auth/login
POST /api/auth/logout
GET /api/auth/me
```

Example account flow with `curl`:

```bash
# Register and save the authentication cookie
curl -c cookies.txt -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"demo-user\",\"password\":\"demo-password-123\"}"

# Use the cookie for protected requests
curl -b cookies.txt http://localhost:8000/api/datasets

# Log in later with the same cookie file
curl -c cookies.txt -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"demo-user\",\"password\":\"demo-password-123\"}"
```

## Step-by-step local setup

### 1. Install prerequisites

Install:

- Python 3.11 or newer
- Node.js 18 or newer
- npm 9 or newer
- Git

### 2. Create and activate a Python environment

From the repository root on Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

On macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install backend dependencies

```bash
python -m pip install --upgrade pip
pip install -r backend/requirements.txt
```

### 4. Configure backend environment variables

Create `backend/.env`:

```env
SECRET_KEY=replace-with-a-long-random-secret
GEMINI_API_KEY=optional-gemini-key
KAGGLE_USERNAME=optional-kaggle-username
KAGGLE_KEY=optional-kaggle-key
DATABASE_URL=sqlite:///./app.db
ENFORCE_TENANT_ISOLATION=true
ALLOW_CODE_EXECUTION=false
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
```

Important:

- `SECRET_KEY` is required and must not use a default value.
- Keep `ALLOW_CODE_EXECUTION=false` unless code runs in a separately isolated
  sandbox.
- Gemini and Kaggle credentials are optional. Features that require them return
  an explicit unavailable response when they are not configured.
- The database setting is retained for database-backed utilities, but the
  primary dataset, model, session, and chat runtime remains in memory.

### 5. Start the backend

From the repository root:

```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Verify that it is running:

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{"status":"healthy","gpu":false}
```

### 6. Install frontend dependencies

Open a second terminal at the repository root:

```bash
npm --prefix frontend install
```

### 7. Configure and start the frontend

Create or update `frontend/.env.development`:

```env
VITE_API_URL=http://localhost:8000
```

Start Vite:

```bash
npm --prefix frontend run dev
```

Open the URL printed by Vite, usually:

```text
http://localhost:5173
```

Register an account, upload a dataset, and use the sidebar to open Search,
Cleaning, Features, EDA, AutoML, Statistics, Chat, and Reports.

## Common user workflow

1. Open the frontend.
2. Register or sign in.
3. Open **Dataset Search**.
4. Upload a CSV or spreadsheet, or search Kaggle if credentials are available.
5. Select the uploaded dataset.
6. Use **Cleaning** and **Feature Engineering** if the data needs changes.
7. Open **Auto EDA** to inspect data quality, statistics, and correlations.
8. Open **Auto ML**, select features and a target, and train a model.
9. Review metrics and feature importance.
10. Use prediction, chat, or report generation for follow-up analysis.

## Backend API groups

All protected routes are prefixed with `/api`.

| Area | Main endpoints |
| --- | --- |
| Authentication | `/api/auth/register`, `/api/auth/login`, `/api/auth/logout`, `/api/auth/me` |
| Sessions | `/api/sessions`, `/api/sessions/{session_id}/history` |
| Datasets | `/api/datasets`, `/api/datasets/upload`, `/api/datasets/{dataset_id}` |
| Cleaning | `/api/datasets/{dataset_id}/clean` |
| Features | `/api/datasets/{dataset_id}/feature-engineer` |
| Preprocessing | `/api/preprocess`, `/api/preprocess/options` |
| EDA | `/api/eda/analyze`, `/api/eda/statistical-tests`, `/api/analysis/auto` |
| Statistics | `/api/statistics-math/analyze` |
| Machine learning | `/api/ml/train`, `/api/ml/train-selected`, `/api/ml/cluster` |
| Prediction | `/api/predict` |
| Explainability | `/api/explain/shap`, `/api/explain/feature-importance` |
| Queries | `/api/query`, `/api/query/enhanced`, `/api/query/langchain` |
| Chat | `/api/chat`, `/api/chat/history/{session_id}` |
| Reports | `/api/report/generate`, `/api/reports/history/{session_id}` |
| Kaggle | `/api/kaggle/search`, `/api/kaggle/download` |

Interactive API documentation is available while the backend is running:

```text
http://localhost:8000/docs
http://localhost:8000/redoc
```

## Runtime limits and eviction

Runtime state is tenant-scoped and bounded. The backend can limit:

- Maximum number of tenants
- Datasets per tenant
- Total dataframe memory per tenant
- Models per tenant
- Preprocessors per tenant
- Chat sessions per tenant
- Messages per chat session
- Upload size, rows, columns, and image pixels

When a configured capacity is reached, the API returns HTTP `429` with a
descriptive message. Tenant state can use LRU or TTL eviction.

Relevant environment variables include:

```env
MAX_TENANTS=100
MAX_DATASETS_PER_TENANT=100
MAX_DATASET_MEMORY_MB_PER_TENANT=512
MAX_MODELS_PER_TENANT=100
MAX_PREPROCESSORS_PER_TENANT=100
MAX_CHAT_SESSIONS_PER_TENANT=100
MAX_CHAT_MESSAGES_PER_SESSION=1000
TENANT_EVICTION_MODE=lru
TENANT_TTL_SECONDS=3600
```

## Testing and quality checks

### Backend tests

From the repository root:

```bash
pytest -q backend/tests/
```

The backend tests cover authentication, tenant isolation, runtime limits,
eviction, data upload, EDA/statistical reference values, model-training
leakage prevention, prediction round trips, and Kaggle credential concurrency.

For coverage:

```bash
pytest -q backend/tests/ \
  --cov=backend/app \
  --cov-report=xml:backend/coverage.xml
```

### Frontend tests, lint, and build

```bash
npm --prefix frontend run test
npm --prefix frontend run lint
npm --prefix frontend run build
```

Vitest tests cover:

- Dataset upload request construction and cookie credentials
- AutoML selection and mocked training flow

### Full CI-equivalent commands

The GitHub Actions workflow runs:

```bash
cd backend
pytest -p no:langsmith_plugin -p pytest_asyncio.plugin \
  -p pytest_cov.plugin tests/ -v \
  --cov=app --cov-report=xml:coverage.xml

black --check backend/
cd backend && flake8 . --config setup.cfg

npm ci --prefix frontend
npm --prefix frontend run lint
npm --prefix frontend run build
```

## Docker Compose

Docker Compose starts both services:

```bash
docker compose up --build
```

Services:

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`
- Backend health: `http://localhost:8000/health`

Set at least `SECRET_KEY` before starting Compose. For example, in a local
shell:

```bash
SECRET_KEY=replace-with-a-long-random-secret docker compose up --build
```

On PowerShell:

```powershell
$env:SECRET_KEY = "replace-with-a-long-random-secret"
docker compose up --build
```

## Deployment

### Render

`render.yaml` defines:

- A Python backend rooted at `backend/`
- A static frontend rooted at `frontend/`
- `VITE_API_URL` pointing the frontend to the backend

Configure these backend values as Render secrets or environment variables:

- `SECRET_KEY`
- `GEMINI_API_KEY` when Gemini features are needed
- `KAGGLE_USERNAME` and `KAGGLE_KEY` when Kaggle features are needed
- `DATABASE_URL` when database-backed utilities are needed
- `ALLOWED_ORIGINS` with the deployed frontend origin

The Render backend starts with:

```bash
PYTHONPATH=. uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### Vercel

The root `vercel.json` is configured for the frontend monorepo layout:

```text
Install: npm --prefix frontend install
Build:   npm --prefix frontend run build
Output:  frontend/dist
```

Set only:

```text
VITE_API_URL
```

Never put `SECRET_KEY`, Kaggle keys, Gemini keys, JWT signing material, or
tenant credentials in frontend environment variables. Any `VITE_*` value is
compiled into the browser bundle.

### GitHub Pages

The `deploy-pages.yml` workflow builds the frontend and publishes the Vite
output as a GitHub Pages artifact. Configure `VITE_API_URL` in the workflow or
deployment environment to point to the deployed backend.

## Security guidance

- Use a unique, long random `SECRET_KEY` in every deployed environment.
- Use HTTPS in production.
- Set `AUTH_COOKIE_SECURE=true` when serving over HTTPS.
- Use `AUTH_COOKIE_SAMESITE=none` only when cross-site cookies are required, and
  pair it with secure cookies.
- Keep frontend and backend origins explicit in `ALLOWED_ORIGINS`.
- Keep code execution disabled unless a separate sandbox is available.
- Do not commit `.env` files, API keys, Kaggle credentials, or generated data.
- Kaggle credentials entered in the frontend are held only in memory and sent
  only with the request that needs them.

## Troubleshooting

### The frontend returns 401

Register or sign in again and ensure browser cookies are enabled. The backend
must be reachable at the configured `VITE_API_URL`.

### The browser reports a CORS error

Add the exact frontend origin, including scheme and port, to
`ALLOWED_ORIGINS`. Restart the backend after changing environment variables.

### The backend rejects startup

Check that `SECRET_KEY` is set and is not one of the default placeholder
values. Also confirm that dependencies were installed into the active Python
environment.

### Uploaded data disappeared

This is expected after a backend restart because runtime datasets and trained
models are intentionally stored in memory.

### Kaggle search is unavailable

Supply `kaggle_username` and `kaggle_key` for the request or configure backend
Kaggle credentials. The frontend does not persist Kaggle credentials in
`localStorage`.

## Project status

The application is suitable for local development, demonstrations, and
reviewable analysis workflows. It is not a fully persistent production data
platform: runtime state is in memory, optional integrations require external
credentials, and deployment operators must provide HTTPS, secret management,
resource limits, monitoring, and a persistent storage strategy when needed.

## License

MIT
