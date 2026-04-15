# Gemini Benchmark Studio

Standalone product for benchmarking Gemini response modes with:

- React UX
- FastAPI backend
- Supervisor-worker multi-agent orchestration
- Prompt templates for user data

## Features

- API key input from UI for each run (not persisted)
- Checkbox mode selection
- Best known mode defaults preselected:
  - stack: `google_genai`
  - model: `gemini-2.5-flash`
  - mode: `streaming`
  - thinking: `off`
  - cache: `implicit_reuse`
- Prompt template + variable editor and preview
- Benchmark run artifacts and recommendation report

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
- `POST /api/benchmark/run`

## Notes

- This app is independent from tutorial benchmark code.
- API keys are used in-memory per request and never written to output files.
