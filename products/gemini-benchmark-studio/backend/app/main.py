from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from agent.supervisor_agent import SupervisorAgent
from app.defaults import best_mode_defaults
from app.schemas import (
    BenchmarkRequest,
    BenchmarkResponse,
    DefaultModesResponse,
    PromptPreviewRequest,
    PromptPreviewResponse,
)
from app.services.prompt_template import render_prompt_template


app = FastAPI(title="Gemini Benchmark Studio API", version="0.1.0")
supervisor = SupervisorAgent()

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


@app.post("/api/benchmark/run", response_model=BenchmarkResponse)
def run_benchmark(request: BenchmarkRequest) -> BenchmarkResponse:
    if not request.api_key:
        raise HTTPException(status_code=400, detail="api_key is required")
    try:
        result = supervisor.run(request)
        return result.response
    except Exception as exc:
        return supervisor.fallback_response(str(exc))

