from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from agent.supervisor_agent import SupervisorAgent
from app.defaults import best_mode_defaults
from app.schemas import (
    BenchmarkRequest,
    BenchmarkResponse,
    DefaultModesResponse,
    PromptPreviewRequest,
    PromptPreviewResponse,
    RunHistoryItem,
    RunHistoryResponse,
    UploadContextResponse,
)
from app.services.data_upload import extract_context_from_bytes
from app.services.history_store import BenchmarkHistoryStore
from app.services.prompt_template import render_prompt_template


app = FastAPI(title="Gemini Benchmark Studio API", version="0.1.0")
supervisor = SupervisorAgent()
history_store = BenchmarkHistoryStore()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/benchmark/default-modes", response_model=DefaultModesResponse)
def default_modes() -> DefaultModesResponse:
    return DefaultModesResponse(defaults=best_mode_defaults())


@app.post("/api/prompt/preview", response_model=PromptPreviewResponse)
def prompt_preview(request: PromptPreviewRequest) -> PromptPreviewResponse:
    rendered, missing = render_prompt_template(request.template, request.variables)
    return PromptPreviewResponse(rendered_prompt=rendered, missing_variables=missing)


@app.post("/api/prompt/upload-context", response_model=UploadContextResponse)
async def upload_context_file(
    file: UploadFile = File(...),
    variable_key: str = Query(default="data_context"),
) -> UploadContextResponse:
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    context_text, byte_count = extract_context_from_bytes(content, file.filename or "uploaded_file")
    preview = context_text[:300]
    return UploadContextResponse(
        variable_key=variable_key,
        bytes_received=byte_count,
        chars_extracted=len(context_text),
        context_text=context_text,
        preview=preview,
    )


@app.post("/api/benchmark/run", response_model=BenchmarkResponse)
def run_benchmark(request: BenchmarkRequest) -> BenchmarkResponse:
    if not request.api_key:
        raise HTTPException(status_code=400, detail="api_key is required")
    try:
        result = supervisor.run(request)
        request_snapshot = request.model_dump(exclude={"api_key"})
        history_store.save_run(
            run_id=result.response.run_id,
            request_snapshot=request_snapshot,
            best_scenario_id=result.response.recommendation.best_scenario_id,
            summaries_count=len(result.response.summaries),
            artifacts=result.response.artifacts,
        )
        return result.response
    except Exception as exc:
        return supervisor.fallback_response(str(exc))


@app.get("/api/benchmark/history", response_model=RunHistoryResponse)
def benchmark_history(limit: int = Query(default=25, ge=1, le=200)) -> RunHistoryResponse:
    rows = history_store.list_runs(limit=limit)
    return RunHistoryResponse(runs=[RunHistoryItem(**row) for row in rows])

