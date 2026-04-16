export type ModeSelection = {
  streaming: boolean;
  thinking: boolean;
  implicit_cache: boolean;
  explicit_cache: boolean;
};

export type VertexConfig = {
  project_id: string;
  location: string;
  endpoint_id: string;
  access_token?: string;
};

export type BenchmarkRequest = {
  api_key?: string;
  stacks: string[];
  models: string[];
  trials: number;
  warmup_trials: number;
  max_output_tokens: number;
  temperature: number;
  timeout_s: number;
  mode_selection: ModeSelection;
  thinking_token_budget?: number;
  prompt_template: string;
  prompt_variables: Record<string, string>;
  vertex_config?: VertexConfig;
  include_long_context: boolean;
  recommendation_objective?: "lowest_latency" | "balanced" | "reliability_first";
  schedule_enabled?: boolean;
  schedule_start_at?: string;
  schedule_window_minutes?: number;
};

export type ScenarioSummary = {
  scenario_id: string;
  stack: string;
  model: string;
  mode: string;
  thinking: boolean;
  thinking_token_budget: number;
  cache_strategy: string;
  prompt_type: string;
  samples: number;
  ok_count: number;
  unsupported_count: number;
  error_count: number;
  ttft_p50_s: number | null;
  ttft_p95_s: number | null;
  e2e_p50_s: number | null;
  tokens_per_s_avg: number | null;
  ttft_definition: string;
  note: string | null;
};

export type BenchmarkResponse = {
  run_id: string;
  rendered_prompt: string;
  summaries: ScenarioSummary[];
  recommendation: {
    best_scenario_id: string | null;
    rationale: string;
    alternatives: string[];
    ranked_scenarios: {
      scenario_id: string;
      score: number;
      ttft_p50_s: number | null;
      ttft_p95_s: number | null;
      e2e_p50_s: number | null;
      tokens_per_s_avg: number | null;
      success_rate: number;
      error_rate: number;
      unsupported_rate: number;
    }[];
    disqualified_scenarios: {
      scenario_id: string;
      reason: string;
    }[];
    reliability_score: number;
    confidence: string;
    objective: string;
  };
  reasoning_trace: string[];
  artifacts: Record<string, string>;
};

export type RunHistoryItem = {
  saved_at: string;
  run_id: string;
  best_scenario_id: string | null;
  summaries_count: number;
  request: Record<string, unknown>;
  artifacts: Record<string, string>;
};

export type DefaultModesResponse = {
  defaults: {
    stack: string;
    model: string;
    streaming: boolean;
    thinking: boolean;
    thinking_token_budget: number;
    implicit_cache: boolean;
    explicit_cache: boolean;
    trials: number;
  };
};

export type RunHistoryResponse = {
  runs: RunHistoryItem[];
};

export type PromptOptimizationRequest = {
  template: string;
  variables: Record<string, string>;
  objective: "lowest_latency" | "highest_quality" | "balanced";
  variant_count: number;
  locked_phrases: string[];
};

export type PromptOptimizationVariant = {
  variant_id: string;
  template: string;
  rendered_prompt: string;
  quality_proxy_score: number;
  reasoning: string;
};

export type PromptOptimizationResponse = {
  objective: string;
  winner_variant_id: string;
  winner_template: string;
  variants: PromptOptimizationVariant[];
  trace: string[];
};

export type PromptOptimizeBenchmarkRequest = {
  benchmark: BenchmarkRequest;
  optimization: PromptOptimizationRequest;
  use_winner_template: boolean;
};

export type PromptOptimizeBenchmarkResponse = {
  optimization: PromptOptimizationResponse;
  benchmark: BenchmarkResponse;
};

export type PromptTokenCountRequest = {
  stack: string;
  model: string;
  api_key?: string;
  template: string;
  variables: Record<string, string>;
  vertex_config?: VertexConfig;
  mode_selection: ModeSelection;
  include_long_context: boolean;
  calls_for_savings: number;
};

export type PromptTokenBreakdownItem = {
  prompt_type: string;
  strategy: string;
  baseline_request_tokens: number;
  request_tokens: number;
  cache_create_tokens: number;
  first_call_total_tokens: number;
  subsequent_call_tokens: number;
  savings_vs_baseline_after_n_calls: number;
};

export type PromptTokenCountResponse = {
  rendered_prompt: string;
  token_count: number;
  calls_for_savings: number;
  breakdown: PromptTokenBreakdownItem[];
  note?: string | null;
};

