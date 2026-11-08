# DataScience Assistant

Data science assistant with:
- FastAPI backend for dataset processing, EDA, ML, statistics, and reporting
- React + Vite frontend for interactive workflows

## Architecture

- frontend: React app (Vite)
- backend: FastAPI API and ML/EDA runtime
- infra: deployment manifests
- docs: additional project documentation

## Feature status

- **Implemented:** Dataset upload, in-memory dataset management, EDA, visual summaries,
  model training/comparison, statistics, feature engineering, data cleaning, and PDF
  report generation.
- **Optional integrations:** Gemini-powered analysis, LangChain queries, and Kaggle
  dataset search/download require their corresponding credentials.
- **Not persisted:** Uploaded datasets, trained models, sessions, and chat history are
  held in memory and are lost whenever the backend restarts.

## Security Model

Runtime API is protected by:
- Argon2-hashed user accounts
- short-lived JWTs stored in HttpOnly cookies
- tenant isolation derived from the authenticated user ID

Backend defaults enforce:
- tenant isolation in in-memory runtime stores
- code execution disabled unless explicitly enabled

## Local Development

### 1. Backend setup

From repository root:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r backend/requirements.txt
```

Create backend/.env (or edit existing) with at least:

```env
GEMINI_API_KEY=your_gemini_key
SECRET_KEY=your_strong_secret
ENFORCE_TENANT_ISOLATION=true
ALLOW_CODE_EXECUTION=false
```

Run backend:

```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 2. Frontend setup

```bash
npm --prefix frontend install
npm --prefix frontend run dev
```

Use frontend/.env.development:

```env
VITE_API_URL=http://localhost:8000
```

## Testing and Validation

From repository root:

```bash
pytest -q
npm --prefix frontend run build
```

## Deployment

### Backend

- Container deployment is supported via the backend Dockerfile and deployment manifests.
- Ensure SECRET_KEY and any required integration credentials are provided from secrets.
- Keep ALLOW_CODE_EXECUTION=false unless you have strong sandbox isolation
- If code execution is enabled, also set EXECUTION_SANDBOX_CONFIRMED=true only when
  the worker is deployed inside an independently isolated sandbox.

### Frontend (Vercel)

Root vercel.json is configured for monorepo deployment:
- installCommand: npm --prefix frontend install
- buildCommand: npm --prefix frontend run build
- outputDirectory: frontend/dist

Set Vercel environment variables:
- VITE_API_URL

## Environment Variables Reference

Backend important vars:
- GEMINI_API_KEY
- SECRET_KEY
- ENFORCE_TENANT_ISOLATION
- ALLOW_CODE_EXECUTION
- DATABASE_URL

Frontend important vars:
- VITE_API_URL

## License

MIT
