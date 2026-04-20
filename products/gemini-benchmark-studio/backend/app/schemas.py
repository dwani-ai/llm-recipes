from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from app.defaults import DEFAULT_MODELS, DEFAULT_PROMPT_TEMPLATE, DEFAULT_STACKS, best_mode_defaults


class ModeSelection(BaseModel):
    streaming: bool = True
    thinking: bool = False
    implicit_cache: bool = True
    explicit_cache: bool = False


class PromptPreviewRequest(BaseModel):
    template: str = Field(default=DEFAULT_PROMPT_TEMPLATE)
    variables: Dict[str, str] = Field(default_factory=dict)


class PromptPreviewResponse(BaseModel):
    rendered_prompt: str
    missing_variables: List[str]


class PromptTokenCountRequest(BaseModel):
    stack: str = Field(default="google_genai")
    model: str = Field(default="gemini-2.5-flash")
    api_key: Optional[str] = None
    template: str = Field(default=DEFAULT_PROMPT_TEMPLATE)
    variables: Dict[str, str] = Field(default_factory=dict)
    vertex_config: Optional["VertexConfig"] = None
    mode_selection: ModeSelection = Field(default_factory=ModeSelection)
    include_long_context: bool = True
    calls_for_savings: int = Field(default=10, ge=1, le=1000)


class PromptTokenBreakdownItem(BaseModel):
    prompt_type: str
    strategy: str
    baseline_request_tokens: int
    request_tokens: int
    cache_create_tokens: int = 0
    first_call_total_tokens: int
    subsequent_call_tokens: int
    savings_vs_baseline_after_n_calls: int


class PromptTokenCountResponse(BaseModel):
    rendered_prompt: str
    token_count: int
    calls_for_savings: int
    breakdown: List[PromptTokenBreakdownItem] = Field(default_factory=list)
    note: Optional[str] = None


class PromptOptimizationRequest(BaseModel):
    template: str = Field(default=DEFAULT_PROMPT_TEMPLATE)
    variables: Dict[str, str] = Field(default_factory=dict)
    objective: str = Field(default="balanced")
    variant_count: int = Field(default=3, ge=2, le=8)
    locked_phrases: List[str] = Field(default_factory=list)


class PromptVariant(BaseModel):
    variant_id: str
    template: str
    rendered_prompt: str
    quality_proxy_score: float
    reasoning: str


class PromptOptimizationResponse(BaseModel):
    objective: str
    winner_variant_id: str
    winner_template: str
    variants: List[PromptVariant]
    trace: List[str]


class PromptOptimizeBenchmarkRequest(BaseModel):
    benchmark: "BenchmarkRequest"
    optimization: PromptOptimizationRequest
    use_winner_template: bool = True


class PromptOptimizeBenchmarkResponse(BaseModel):
    optimization: PromptOptimizationResponse
    benchmark: "BenchmarkResponse"
    benchmark_failed: bool = False
    benchmark_error: Optional[str] = None


class UploadContextResponse(BaseModel):
    variable_key: str
    bytes_received: int
    chars_extracted: int
    context_text: str
    preview: str


class VertexConfig(BaseModel):
    project_id: str = Field(min_length=3)
    location: str = Field(default="us-central1", min_length=2)
    endpoint_id: str = Field(default="openapi", min_length=2)
    access_token: Optional[str] = None


class BenchmarkRequest(BaseModel):
    api_key: Optional[str] = None
    stacks: List[str] = Field(default_factory=lambda: list(DEFAULT_STACKS))
    models: List[str] = Field(default_factory=lambda: list(DEFAULT_MODELS))
    trials: int = Field(default=10, ge=1, le=100)
    warmup_trials: int = Field(default=2, ge=0, le=20)
    max_output_tokens: int = Field(default=128, ge=8, le=2048)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    timeout_s: int = Field(default=90, ge=10, le=300)
    mode_selection: ModeSelection = Field(default_factory=ModeSelection)
    thinking_token_budget: int = Field(default=1024, ge=0, le=8192)
    thinking_mode: Literal["auto", "budget", "level"] = Field(default="auto")
    thinking_level: Optional[Literal["minimal", "low", "medium", "high"]] = None
    prompt_template: str = Field(default=DEFAULT_PROMPT_TEMPLATE)
    prompt_variables: Dict[str, str] = Field(default_factory=dict)
    vertex_config: Optional[VertexConfig] = None
    include_long_context: bool = True
    recommendation_objective: Literal["lowest_latency", "balanced", "reliability_first"] = Field(
        default="lowest_latency"
    )
    schedule_enabled: bool = False
    schedule_start_at: Optional[datetime] = None
    schedule_window_minutes: int = Field(default=15, ge=1, le=60)


class ScenarioSummary(BaseModel):
    scenario_id: str
    stack: str
    model: str
    mode: str
    thinking: bool
    thinking_mode: str = "off"
    thinking_level: Optional[str] = None
    thinking_token_budget: int
    cache_strategy: str
    prompt_type: str
    samples: int
    ok_count: int
    unsupported_count: int
    error_count: int
    ttft_p50_s: Optional[float] = None
    ttft_p95_s: Optional[float] = None
    e2e_p50_s: Optional[float] = None
    tokens_per_s_avg: Optional[float] = None
    ttft_definition: str = "first_final_output_token"
    note: Optional[str] = None


class BenchmarkRecommendation(BaseModel):
    best_scenario_id: Optional[str] = None
    rationale: str
    alternatives: List[str] = Field(default_factory=list)
    ranked_scenarios: List[Dict[str, Any]] = Field(default_factory=list)
    disqualified_scenarios: List[Dict[str, str]] = Field(default_factory=list)
    reliability_score: float = 0.0
    confidence: str = "low"
    objective: str = "lowest_latency"


class BenchmarkResponse(BaseModel):
    run_id: str
    status: Literal["ok", "failed"] = "ok"
    error_message: Optional[str] = None
    rendered_prompt: str
    summaries: List[ScenarioSummary]
    recommendation: BenchmarkRecommendation
    reasoning_trace: List[str] = Field(default_factory=list)
    artifacts: Dict[str, str]


class DefaultModesResponse(BaseModel):
    defaults: Dict[str, Any] = Field(default_factory=best_mode_defaults)


class RunHistoryItem(BaseModel):
    saved_at: str
    run_id: str
    best_scenario_id: Optional[str] = None
    summaries_count: int
    request: Dict[str, Any]
    artifacts: Dict[str, str]


class RunHistoryResponse(BaseModel):
    runs: List[RunHistoryItem]


PromptOptimizeBenchmarkRequest.model_rebuild()
PromptOptimizeBenchmarkResponse.model_rebuild()
PromptTokenCountRequest.model_rebuild()


