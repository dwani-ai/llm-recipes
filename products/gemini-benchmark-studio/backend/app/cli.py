import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

from app.defaults import DEFAULT_PROMPT_TEMPLATE
from app.schemas import BenchmarkRequest, ModeSelection, VertexConfig
from app.services.benchmark_runner import BenchmarkRunner
from app.services.prompt_template import render_prompt_template


def parse_kv_var(value: str) -> Tuple[str, str]:
    if "=" not in value:
        raise ValueError(f"Invalid --var value '{value}'. Expected KEY=VALUE format.")
    key, raw = value.split("=", 1)
    key = key.strip()
    if not key:
        raise ValueError(f"Invalid --var value '{value}'. Key cannot be empty.")
    return key, raw


def load_variables_json(path: str) -> Dict[str, str]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Variables JSON must be an object of key/value pairs.")
    return {str(k): str(v) for k, v in payload.items()}


def merge_variables(file_vars: Dict[str, str], cli_vars: List[str]) -> Dict[str, str]:
    merged = dict(file_vars)
    for item in cli_vars:
        key, value = parse_kv_var(item)
        merged[key] = value
    return merged


def build_mode_selection(streaming: bool, thinking: bool, cache_intent: str) -> ModeSelection:
    return ModeSelection(
        streaming=streaming,
        thinking=thinking,
        implicit_cache=cache_intent == "implicit_reuse",
        explicit_cache=cache_intent == "explicit_cache",
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run Gemini Benchmark Studio from terminal.",
    )
    parser.add_argument("--api-key", default=None, help="Gemini API key. Falls back to GEMINI_API_KEY.")
    parser.add_argument("--stack", default="google_genai", choices=["google_genai", "openai_compat", "vertex_api"])
    parser.add_argument("--model", default="gemini-2.5-flash")
    parser.add_argument("--trials", type=int, default=10)
    parser.add_argument("--warmup-trials", type=int, default=2)
    parser.add_argument("--streaming", action="store_true", help="Enable streaming mode.")
    parser.add_argument(
        "--no-thinking",
        action="store_true",
        help="Disable thinking. Default is thinking enabled.",
    )
    parser.add_argument("--thinking-token-budget", type=int, default=1024)
    parser.add_argument(
        "--cache-intent",
        choices=["none", "implicit_reuse", "explicit_cache"],
        default="none",
    )
    parser.add_argument("--prompt-template", default=DEFAULT_PROMPT_TEMPLATE)
    parser.add_argument("--var", action="append", default=[], help="Prompt variable in KEY=VALUE format.")
    parser.add_argument("--vars-json", default=None, help="Path to JSON file containing prompt variables.")
    parser.add_argument("--include-long-context", action="store_true")
    parser.add_argument("--recommendation-objective", choices=["lowest_latency", "balanced", "reliability_first"], default="lowest_latency")
    parser.add_argument("--max-output-tokens", type=int, default=128)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--timeout-s", type=int, default=90)
    parser.add_argument("--schedule-start-at", default=None, help="ISO datetime for scheduled run window start.")
    parser.add_argument("--schedule-window-minutes", type=int, default=15)
    parser.add_argument("--vertex-project-id", default=None)
    parser.add_argument("--vertex-location", default="us-central1")
    parser.add_argument("--vertex-endpoint-id", default="openapi")
    parser.add_argument("--vertex-access-token", default=None)
    parser.add_argument("--json", action="store_true", help="Print full run payload as JSON.")
    return parser


def main(argv: List[str] | None = None) -> int:
    args = _parser().parse_args(argv)

    api_key = args.api_key or os.getenv("GEMINI_API_KEY")
    if args.stack in {"google_genai", "openai_compat"} and not api_key:
        print("error: api key is required for google_genai/openai_compat stacks", file=sys.stderr)
        return 2

    file_vars: Dict[str, str] = {}
    if args.vars_json:
        try:
            file_vars = load_variables_json(args.vars_json)
        except Exception as exc:
            print(f"error: failed to load --vars-json: {exc}", file=sys.stderr)
            return 2

    try:
        prompt_variables = merge_variables(file_vars, args.var)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if not prompt_variables:
        prompt_variables = {
            "dataset_name": "benchmark_dataset",
            "goal": "latency analysis",
            "data_context": "",
        }

    rendered_prompt, missing = render_prompt_template(args.prompt_template, prompt_variables)
    if not rendered_prompt:
        print("error: rendered prompt is empty after template expansion", file=sys.stderr)
        return 2

    mode_selection = build_mode_selection(
        streaming=args.streaming,
        thinking=not args.no_thinking,
        cache_intent=args.cache_intent,
    )

    if args.schedule_start_at is not None and args.schedule_window_minutes != 15:
        print("error: CLI currently supports only a 15-minute scheduling window.", file=sys.stderr)
        return 2

    vertex_config = None
    if args.stack == "vertex_api":
        if not args.vertex_project_id:
            print("error: --vertex-project-id is required for vertex_api stack", file=sys.stderr)
            return 2
        vertex_config = VertexConfig(
            project_id=args.vertex_project_id,
            location=args.vertex_location,
            endpoint_id=args.vertex_endpoint_id,
            access_token=args.vertex_access_token,
        )

    try:
        request = BenchmarkRequest(
            api_key=api_key,
            stacks=[args.stack],
            models=[args.model],
            trials=args.trials,
            warmup_trials=args.warmup_trials,
            max_output_tokens=args.max_output_tokens,
            temperature=args.temperature,
            timeout_s=args.timeout_s,
            mode_selection=mode_selection,
            thinking_token_budget=args.thinking_token_budget,
            prompt_template=args.prompt_template,
            prompt_variables=prompt_variables,
            vertex_config=vertex_config,
            include_long_context=args.include_long_context,
            recommendation_objective=args.recommendation_objective,
            schedule_enabled=args.schedule_start_at is not None,
            schedule_start_at=args.schedule_start_at,
            schedule_window_minutes=args.schedule_window_minutes,
        )
    except Exception as exc:
        print(f"error: invalid benchmark request: {exc}", file=sys.stderr)
        return 2

    if missing:
        print(f"warning: missing template variables replaced with empty string: {', '.join(missing)}")

    runner = BenchmarkRunner()
    payload = runner.run(request, rendered_prompt)
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=True))
        return 0

    print(f"run_id: {payload['run_id']}")
    print(f"summary_rows: {len(payload['summaries'])}")
    print("artifacts:")
    for key, value in payload["artifacts"].items():
        print(f"  - {key}: {value}")
    print("\ntop scenarios:")
    for row in payload["summaries"][:5]:
        print(
            f"  {row['scenario_id']} | ttft_p50={row.get('ttft_p50_s')} "
            f"| e2e_p50={row.get('e2e_p50_s')} | ok={row.get('ok_count')}/{row.get('samples')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
