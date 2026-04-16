from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from agent.prompt_optimizer_agent import PromptOptimizerAgent
from agent.supervisor_agent import SupervisorAgent
from app.defaults import best_mode_defaults
from app.schemas import (
    BenchmarkRequest,
    BenchmarkResponse,
    DefaultModesResponse,
    PromptOptimizeBenchmarkRequest,
    PromptOptimizeBenchmarkResponse,
    PromptTokenCountRequest,
    PromptTokenCountResponse,
    PromptPreviewRequest,
    PromptPreviewResponse,
    PromptOptimizationRequest,
    PromptOptimizationResponse,
    RunHistoryItem,
    RunHistoryResponse,
    UploadContextResponse,
)
from app.services.data_upload import extract_context_from_bytes
from app.services.history_store import BenchmarkHistoryStore
from app.services.prompt_template import render_prompt_template
from app.services.token_counter import TokenCountError, mode_aware_token_breakdown


app = FastAPI(title="Gemini Benchmark Studio API", version="0.1.0")
supervisor = SupervisorAgent()
prompt_optimizer = PromptOptimizerAgent()
history_store = BenchmarkHistoryStore()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _validate_benchmark_request(request: BenchmarkRequest) -> None:
    needs_api_key = any(stack in {"google_genai", "openai_compat"} for stack in request.stacks)
    if needs_api_key and not request.api_key:
        raise HTTPException(status_code=400, detail="api_key is required for google_genai/openai_compat stacks")
    if "vertex_api" in request.stacks and request.vertex_config is None:
        raise HTTPException(status_code=400, detail="vertex_config is required for vertex_api stack")


def _save_run_history(request: BenchmarkRequest, response: BenchmarkResponse) -> None:
    request_snapshot = request.model_dump(exclude={"api_key"})
    if "vertex_config" in request_snapshot and isinstance(request_snapshot["vertex_config"], dict):
        request_snapshot["vertex_config"].pop("access_token", None)
    history_store.save_run(
        run_id=response.run_id,
        request_snapshot=request_snapshot,
        best_scenario_id=response.recommendation.best_scenario_id,
        summaries_count=len(response.summaries),
        artifacts=response.artifacts,
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


@app.post("/api/prompt/token-count", response_model=PromptTokenCountResponse)
def prompt_token_count(request: PromptTokenCountRequest) -> PromptTokenCountResponse:
    rendered, missing = render_prompt_template(request.template, request.variables)
    note = None
    if missing:
        note = f"Missing variables replaced with empty string: {', '.join(missing)}"
    try:
        token_data = mode_aware_token_breakdown(
            stack=request.stack,
            model=request.model,
            api_key=request.api_key,
            vertex_config=request.vertex_config,
            rendered_prompt=rendered,
            prompt_variables=request.variables,
            mode_selection=request.mode_selection,
            include_long_context=request.include_long_context,
            calls_for_savings=request.calls_for_savings,
        )
    except TokenCountError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PromptTokenCountResponse(
        rendered_prompt=rendered,
        token_count=token_data["token_count"],
        calls_for_savings=request.calls_for_savings,
        breakdown=token_data["breakdown"],
        note=note,
    )


@app.post("/api/prompt/optimize", response_model=PromptOptimizationResponse)
def optimize_prompt(request: PromptOptimizationRequest) -> PromptOptimizationResponse:
    return prompt_optimizer.optimize(request)


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
    _validate_benchmark_request(request)
    try:
        result = supervisor.run(request)
        _save_run_history(request, result.response)
        return result.response
    except Exception as exc:
        return supervisor.fallback_response(str(exc))


@app.post("/api/prompt/optimize-and-benchmark", response_model=PromptOptimizeBenchmarkResponse)
def optimize_and_benchmark(request: PromptOptimizeBenchmarkRequest) -> PromptOptimizeBenchmarkResponse:
    _validate_benchmark_request(request.benchmark)
    optimization = prompt_optimizer.optimize(request.optimization)
    benchmark_request = request.benchmark
    if request.use_winner_template:
        benchmark_request = request.benchmark.model_copy(update={"prompt_template": optimization.winner_template})
    try:
        benchmark_result = supervisor.run(benchmark_request).response
        _save_run_history(benchmark_request, benchmark_result)
    except Exception as exc:
        benchmark_result = supervisor.fallback_response(str(exc))
    return PromptOptimizeBenchmarkResponse(optimization=optimization, benchmark=benchmark_result)


@app.get("/api/benchmark/history", response_model=RunHistoryResponse)
def benchmark_history(limit: int = Query(default=25, ge=1, le=200)) -> RunHistoryResponse:
    rows = history_store.list_runs(limit=limit)
    return RunHistoryResponse(runs=[RunHistoryItem(**row) for row in rows])

