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
  prompt_template: string;
  prompt_variables: Record<string, string>;
  vertex_config?: VertexConfig;
  include_long_context: boolean;
};

export type ScenarioSummary = {
  scenario_id: string;
  stack: string;
  model: string;
  mode: string;
  thinking: boolean;
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
    implicit_cache: boolean;
    explicit_cache: boolean;
    trials: number;
  };
};

export type RunHistoryResponse = {
  runs: RunHistoryItem[];
};

