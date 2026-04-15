from typing import Any, Dict, List, Optional

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


class BenchmarkRequest(BaseModel):
    api_key: str = Field(min_length=10)
    stacks: List[str] = Field(default_factory=lambda: list(DEFAULT_STACKS))
    models: List[str] = Field(default_factory=lambda: list(DEFAULT_MODELS))
    trials: int = Field(default=10, ge=1, le=100)
    warmup_trials: int = Field(default=2, ge=0, le=20)
    max_output_tokens: int = Field(default=128, ge=8, le=2048)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    timeout_s: int = Field(default=90, ge=10, le=300)
    mode_selection: ModeSelection = Field(default_factory=ModeSelection)
    prompt_template: str = Field(default=DEFAULT_PROMPT_TEMPLATE)
    prompt_variables: Dict[str, str] = Field(default_factory=dict)
    include_long_context: bool = True


class ScenarioSummary(BaseModel):
    scenario_id: str
    stack: str
    model: str
    mode: str
    thinking: bool
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
    note: Optional[str] = None


class BenchmarkRecommendation(BaseModel):
    best_scenario_id: Optional[str] = None
    rationale: str
    alternatives: List[str] = Field(default_factory=list)


class BenchmarkResponse(BaseModel):
    run_id: str
    rendered_prompt: str
    summaries: List[ScenarioSummary]
    recommendation: BenchmarkRecommendation
    reasoning_trace: List[str] = Field(default_factory=list)
    artifacts: Dict[str, str]


class DefaultModesResponse(BaseModel):
    defaults: Dict[str, Any] = Field(default_factory=best_mode_defaults)

