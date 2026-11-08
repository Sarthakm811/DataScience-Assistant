# Setup Guide

Last updated: 2026-03-28

This guide covers local setup for the current FastAPI + React architecture.

## 1. Requirements

- Python 3.10+
- Node.js 18+
- npm 9+

## 2. Backend Setup

From repository root:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r backend/requirements.txt
```

Create or update backend/.env:

```env
GEMINI_API_KEY=your_gemini_key
KAGGLE_USERNAME=optional
KAGGLE_KEY=optional
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ds_agent_dev
SECRET_KEY=your_strong_secret
ENFORCE_TENANT_ISOLATION=true
ALLOW_CODE_EXECUTION=false
MAX_EXECUTION_TIME=45
MAX_MEMORY_MB=1536
```

Run backend:

```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Health check:

```bash
curl http://localhost:8000/health
```

## 3. Frontend Setup

Install and run:

```bash
npm --prefix frontend install
npm --prefix frontend run dev
```

Create or update frontend/.env.development:

```env
VITE_API_URL=http://localhost:8000
```

## 4. Authentication

Register or sign in through the frontend. The backend sets a short-lived
HttpOnly cookie; tenant identity is derived from the authenticated user.

The public endpoints are `/` and `/health`. Protected API calls require the
authentication cookie.

Example:

```bash
curl -c cookies.txt -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"your-user\",\"password\":\"your-password\"}"
curl -b cookies.txt "http://localhost:8000/api/datasets"
```

## 5. Tests and Build

Run backend tests:

```bash
pytest -q
```

Run frontend production build:

```bash
npm --prefix frontend run build
```

## 6. Vercel Frontend Deployment

The repository root has vercel.json configured for monorepo frontend build.

Set Vercel environment variables:
- VITE_API_URL

Deploy from main branch.

## 7. Common Issues

1) 401 Unauthorized
- Register or sign in and ensure cookies are enabled

3) CORS blocked
- Add your frontend origin to ALLOWED_ORIGINS on backend

4) Code execution disabled
- This is expected by default
- Enable only if you have proper sandboxing: ALLOW_CODE_EXECUTION=true

## 8. Production Recommendations

- Keep ENFORCE_TENANT_ISOLATION=true
- Keep ALLOW_CODE_EXECUTION=false unless strongly sandboxed
- Use secret manager for SECRET_KEY, DATABASE_URL, API keys
- Add WAF/rate-limiting at ingress
