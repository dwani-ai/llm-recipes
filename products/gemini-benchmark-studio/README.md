# Gemini Benchmark Studio

Standalone product for benchmarking Gemini response modes with:

- React UX
- FastAPI backend
- Supervisor-worker multi-agent orchestration
- Prompt templates for user data
- Upload-to-context for user data files
- Persistent benchmark run history (without API key storage)
- Docker Compose integrated build and run

## Features

- API key input from UI for each run (not persisted)
- Checkbox mode selection
- Stack selection: `google_genai`, `openai_compat`, `vertex_api`
- Best known mode defaults preselected:
  - stack: `google_genai`
  - model: `gemini-2.5-flash`
  - mode: `streaming`
  - thinking: `off`
  - cache: `implicit_reuse`
- Prompt template + variable editor and preview
- Agent-assisted prompt optimization (objective-based variants + winner selection)
- One-click optimize + benchmark flow (kept separate from standalone optimize and benchmark actions)
- Data file upload into `data_context` prompt variable
- Vertex API credentials form (project, location, endpoint, optional access token)
- Benchmark run artifacts and recommendation report
- Run history endpoint and UI table for recent runs

## Project Layout

- `frontend/` - React + Vite app
- `backend/` - FastAPI API + benchmark engine + multi-agent layer

## Run Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Run Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend expects backend at `http://localhost:8000`.

## API Endpoints

- `GET /api/health`
- `GET /api/benchmark/default-modes`
- `POST /api/prompt/preview`
- `POST /api/prompt/token-count` (exact provider token count)
- `POST /api/prompt/optimize`
- `POST /api/prompt/optimize-and-benchmark`
- `POST /api/prompt/upload-context`
- `POST /api/benchmark/run`
- `GET /api/benchmark/history`

For `vertex_api`, send `vertex_config` with:

- `project_id`
- `location` (e.g. `us-central1`)
- `endpoint_id` (use `openapi` for Gemini OpenAPI endpoint on Vertex)
- `access_token` (optional; if omitted, backend uses ADC via `google-auth`)

## Run with Docker Compose

```bash
cd /home/sachin/code/llm-recipes/products/gemini-benchmark-studio
docker compose up --build
```

Services:

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`

Stop services:

```bash
docker compose down
```

## Notes

- This app is independent from tutorial benchmark code.
- API keys are used in-memory per request and never written to output files.
- Run history persists benchmark metadata only; request snapshots exclude `api_key`.
