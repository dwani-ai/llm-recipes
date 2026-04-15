import argparse
import csv
import itertools
import json
import os
import statistics
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    import yaml
except ImportError:  # pragma: no cover - optional dependency
    yaml = None

try:
    from google import genai
except ImportError:  # pragma: no cover - optional dependency
    genai = None

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - optional dependency
    OpenAI = None


DEFAULT_CONFIG: Dict[str, Any] = {
    "stacks": ["google_genai", "openai_compat"],
    "models": ["gemini-2.5-flash", "gemini-2.5-pro"],
    "modes": ["streaming", "non_streaming"],
    "thinking_modes": ["off", "on"],
    "cache_strategies": ["none", "implicit_reuse", "explicit_cache"],
    "prompt_types": ["short_prompt", "long_context"],
    "trials": 8,
    "warmup_trials": 2,
    "max_output_tokens": 128,
    "temperature": 0.2,
    "timeout_s": 90,
    "output_dir": "outputs/gemini_ttft",
    "openai_base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
    "prompts": {
        "short_prompt": {
            "system": "You are a concise assistant. Keep responses factual.",
            "user": "Summarize why streaming improves user-perceived latency in 4 bullets.",
            "shared_prefix": "",
        },
        "long_context": {
            "system": "You are a performance engineer. Respond in concise bullets.",
            "shared_prefix": (
                "Benchmark context:\n"
                "- We compare streaming and non-streaming requests.\n"
                "- We compare thinking enabled and disabled.\n"
                "- We compare cache strategies for repeated prefixes.\n"
                "- Report TTFT and end-to-end latency.\n"
            ),
            "user": "Given the context above, propose 5 low-risk latency optimizations.",
        },
    },
}


@dataclass(frozen=True)
class Scenario:
    stack: str
    model: str
    mode: str
    thinking: str
    cache_strategy: str
    prompt_type: str
    trials: int
    warmup_trials: int
    max_output_tokens: int
    temperature: float
    timeout_s: int

    @property
    def scenario_id(self) -> str:
        return (
            f"{self.stack}|{self.model}|{self.mode}|thinking_{self.thinking}|"
            f"cache_{self.cache_strategy}|{self.prompt_type}"
        )


def percentile(values: List[float], p: float) -> Optional[float]:
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    sorted_values = sorted(values)
    index = (len(sorted_values) - 1) * (p / 100.0)
    lower = int(index)
    upper = min(lower + 1, len(sorted_values) - 1)
    if lower == upper:
        return sorted_values[lower]
    weight = index - lower
    return sorted_values[lower] * (1.0 - weight) + sorted_values[upper] * weight


def utc_now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def load_config(path: Optional[Path]) -> Dict[str, Any]:
    if path is None:
        return DEFAULT_CONFIG
    if yaml is None:
        raise RuntimeError("PyYAML is required when using --config. Install `pyyaml`.")
    loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    merged = dict(DEFAULT_CONFIG)
    merged.update({k: v for k, v in loaded.items() if k != "prompts"})
    merged_prompts = dict(DEFAULT_CONFIG["prompts"])
    merged_prompts.update(loaded.get("prompts", {}))
    merged["prompts"] = merged_prompts
    return merged


def build_scenarios(config: Dict[str, Any]) -> List[Scenario]:
    scenarios: List[Scenario] = []
    for stack, model, mode, thinking, cache_strategy, prompt_type in itertools.product(
        config["stacks"],
        config["models"],
        config["modes"],
        config["thinking_modes"],
        config["cache_strategies"],
        config["prompt_types"],
    ):
        scenarios.append(
            Scenario(
                stack=stack,
                model=model,
                mode=mode,
                thinking=thinking,
                cache_strategy=cache_strategy,
                prompt_type=prompt_type,
                trials=int(config["trials"]),
                warmup_trials=int(config["warmup_trials"]),
                max_output_tokens=int(config["max_output_tokens"]),
                temperature=float(config["temperature"]),
                timeout_s=int(config["timeout_s"]),
            )
        )
    return scenarios


def normalize_text_parts(parts: Iterable[str]) -> str:
    return "".join(part for part in parts if part)


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, len(text.split()))


class GoogleGenAIAdapter:
    def __init__(self, api_key: str) -> None:
        if genai is None:
            raise RuntimeError("google-genai is not installed.")
        self.client = genai.Client(api_key=api_key)
        self._explicit_cache_keys: Dict[Tuple[str, str], Any] = {}

    @staticmethod
    def _build_prompt(prompt_cfg: Dict[str, str], cache_strategy: str) -> str:
        shared_prefix = prompt_cfg.get("shared_prefix", "")
        user_prompt = prompt_cfg.get("user", "")
        if cache_strategy == "none":
            return user_prompt
        return f"{shared_prefix}\n{user_prompt}".strip()

    @staticmethod
    def _thinking_payload(thinking: str) -> Optional[Dict[str, Any]]:
        if thinking == "off":
            return {"thinking_config": {"thinking_budget": 0}}
        if thinking == "on":
            # Keeps reasoning enabled while capping runaway token usage.
            return {"thinking_config": {"thinking_budget": 1024}}
        return None

    def _build_config(self, scenario: Scenario, explicit_cache_name: Optional[str]) -> Dict[str, Any]:
        config: Dict[str, Any] = {
            "max_output_tokens": scenario.max_output_tokens,
            "temperature": scenario.temperature,
        }
        thinking_cfg = self._thinking_payload(scenario.thinking)
        if thinking_cfg:
            config.update(thinking_cfg)
        if explicit_cache_name:
            config["cached_content"] = explicit_cache_name
        return config

    def _ensure_explicit_cache(
        self, scenario: Scenario, prompt_cfg: Dict[str, str]
    ) -> Tuple[Optional[str], Optional[str]]:
        cache_key = (scenario.model, scenario.prompt_type)
        if cache_key in self._explicit_cache_keys:
            return self._explicit_cache_keys[cache_key], None
        if not hasattr(self.client, "caches"):
            return None, "google_genai_cache_api_not_available"
        shared_prefix = prompt_cfg.get("shared_prefix", "")
        if not shared_prefix:
            return None, "no_shared_prefix_for_explicit_cache"
        try:
            cache_obj = self.client.caches.create(
                model=scenario.model,
                config={
                    "contents": [{"role": "user", "parts": [{"text": shared_prefix}]}],
                    "ttl": "3600s",
                },
            )
            cache_name = getattr(cache_obj, "name", None)
            if not cache_name:
                return None, "explicit_cache_created_without_name"
            self._explicit_cache_keys[cache_key] = cache_name
            return cache_name, None
        except Exception as exc:  # pragma: no cover - network and API dependent
            return None, f"explicit_cache_create_failed:{type(exc).__name__}"

    def run_once(self, scenario: Scenario, prompt_cfg: Dict[str, str]) -> Dict[str, Any]:
        if scenario.mode not in {"streaming", "non_streaming"}:
            return {"status": "unsupported", "reason": "invalid_mode"}

        explicit_cache_name = None
        if scenario.cache_strategy == "explicit_cache":
            explicit_cache_name, cache_error = self._ensure_explicit_cache(scenario, prompt_cfg)
            if cache_error:
                return {"status": "unsupported", "reason": cache_error}

        prompt = self._build_prompt(prompt_cfg, scenario.cache_strategy)
        contents = [
            {"role": "user", "parts": [{"text": prompt}]},
        ]
        config = self._build_config(scenario, explicit_cache_name)

        if scenario.mode == "streaming":
            return self._run_streaming(scenario, contents, config)
        return self._run_non_streaming(scenario, contents, config)

    def _run_streaming(
        self, scenario: Scenario, contents: List[Dict[str, Any]], config: Dict[str, Any]
    ) -> Dict[str, Any]:
        start = time.perf_counter()
        first_chunk_at: Optional[float] = None
        output_parts: List[str] = []
        try:
            stream = self.client.models.generate_content_stream(
                model=scenario.model,
                contents=contents,
                config=config,
            )
            for chunk in stream:
                if first_chunk_at is None:
                    first_chunk_at = time.perf_counter()
                output_parts.append(getattr(chunk, "text", "") or "")
            end = time.perf_counter()
        except Exception as exc:  # pragma: no cover - network and API dependent
            return {"status": "error", "error": f"{type(exc).__name__}: {exc}"}

        text = normalize_text_parts(output_parts)
        ttft_s = (first_chunk_at - start) if first_chunk_at else (end - start)
        total_s = end - start
        output_tokens = estimate_tokens(text)
        return {
            "status": "ok",
            "ttft_s": ttft_s,
            "e2e_s": total_s,
            "output_tokens": output_tokens,
            "tokens_per_s": (output_tokens / total_s) if total_s > 0 else None,
            "response_preview": text[:200],
        }

    def _run_non_streaming(
        self, scenario: Scenario, contents: List[Dict[str, Any]], config: Dict[str, Any]
    ) -> Dict[str, Any]:
        start = time.perf_counter()
        try:
            response = self.client.models.generate_content(
                model=scenario.model,
                contents=contents,
                config=config,
            )
            end = time.perf_counter()
        except Exception as exc:  # pragma: no cover - network and API dependent
            return {"status": "error", "error": f"{type(exc).__name__}: {exc}"}

        text = getattr(response, "text", "") or ""
        usage = getattr(response, "usage_metadata", None)
        output_tokens = None
        if usage is not None:
            output_tokens = getattr(usage, "candidates_token_count", None)
        if output_tokens is None:
            output_tokens = estimate_tokens(text)
        total_s = end - start
        return {
            "status": "ok",
            # Non-streaming does not expose first token timing; we log payload-arrival proxy.
            "ttft_s": total_s,
            "e2e_s": total_s,
            "output_tokens": output_tokens,
            "tokens_per_s": (output_tokens / total_s) if total_s > 0 else None,
            "response_preview": text[:200],
        }


class OpenAICompatGeminiAdapter:
    def __init__(self, api_key: str, base_url: str) -> None:
        if OpenAI is None:
            raise RuntimeError("openai package is not installed.")
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    @staticmethod
    def _messages(prompt_cfg: Dict[str, str], cache_strategy: str) -> List[Dict[str, str]]:
        system_prompt = prompt_cfg.get("system", "")
        user_prompt = prompt_cfg.get("user", "")
        shared_prefix = prompt_cfg.get("shared_prefix", "")
        if cache_strategy == "none":
            prompt = user_prompt
        else:
            prompt = f"{shared_prefix}\n{user_prompt}".strip()
        messages: List[Dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return messages

    def run_once(self, scenario: Scenario, prompt_cfg: Dict[str, str]) -> Dict[str, Any]:
        if scenario.thinking == "on":
            return {"status": "unsupported", "reason": "thinking_toggle_not_supported_on_openai_compat_adapter"}
        if scenario.cache_strategy == "explicit_cache":
            return {"status": "unsupported", "reason": "explicit_cache_not_supported_on_openai_compat_adapter"}
        messages = self._messages(prompt_cfg, scenario.cache_strategy)
        if scenario.mode == "streaming":
            return self._run_streaming(scenario, messages)
        if scenario.mode == "non_streaming":
            return self._run_non_streaming(scenario, messages)
        return {"status": "unsupported", "reason": "invalid_mode"}

    def _run_streaming(self, scenario: Scenario, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        start = time.perf_counter()
        first_chunk_at: Optional[float] = None
        output_parts: List[str] = []
        try:
            stream = self.client.chat.completions.create(
                model=scenario.model,
                messages=messages,
                max_tokens=scenario.max_output_tokens,
                temperature=scenario.temperature,
                stream=True,
                timeout=scenario.timeout_s,
            )
            for chunk in stream:
                if first_chunk_at is None:
                    first_chunk_at = time.perf_counter()
                delta = chunk.choices[0].delta
                piece = getattr(delta, "content", "") or ""
                output_parts.append(piece)
            end = time.perf_counter()
        except Exception as exc:  # pragma: no cover - network and API dependent
            return {"status": "error", "error": f"{type(exc).__name__}: {exc}"}

        text = normalize_text_parts(output_parts)
        ttft_s = (first_chunk_at - start) if first_chunk_at else (end - start)
        total_s = end - start
        output_tokens = estimate_tokens(text)
        return {
            "status": "ok",
            "ttft_s": ttft_s,
            "e2e_s": total_s,
            "output_tokens": output_tokens,
            "tokens_per_s": (output_tokens / total_s) if total_s > 0 else None,
            "response_preview": text[:200],
        }

    def _run_non_streaming(self, scenario: Scenario, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        start = time.perf_counter()
        try:
            response = self.client.chat.completions.create(
                model=scenario.model,
                messages=messages,
                max_tokens=scenario.max_output_tokens,
                temperature=scenario.temperature,
                stream=False,
                timeout=scenario.timeout_s,
            )
            end = time.perf_counter()
        except Exception as exc:  # pragma: no cover - network and API dependent
            return {"status": "error", "error": f"{type(exc).__name__}: {exc}"}

        text = response.choices[0].message.content or ""
        usage = getattr(response, "usage", None)
        output_tokens = getattr(usage, "completion_tokens", None) if usage else None
        if output_tokens is None:
            output_tokens = estimate_tokens(text)
        total_s = end - start
        return {
            "status": "ok",
            "ttft_s": total_s,
            "e2e_s": total_s,
            "output_tokens": output_tokens,
            "tokens_per_s": (output_tokens / total_s) if total_s > 0 else None,
            "response_preview": text[:200],
        }


def adapter_for_scenario(scenario: Scenario, config: Dict[str, Any]) -> Any:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is required.")
    if scenario.stack == "google_genai":
        return GoogleGenAIAdapter(api_key=api_key)
    if scenario.stack == "openai_compat":
        return OpenAICompatGeminiAdapter(
            api_key=api_key,
            base_url=config["openai_base_url"],
        )
    raise RuntimeError(f"Unsupported stack: {scenario.stack}")


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")


def write_summary_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    columns = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def aggregate(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for row in results:
        if row["is_warmup"]:
            continue
        grouped.setdefault(row["scenario_id"], []).append(row)

    summaries: List[Dict[str, Any]] = []
    for scenario_id, rows in grouped.items():
        ttfts = [r["ttft_s"] for r in rows if r["status"] == "ok" and r["ttft_s"] is not None]
        e2es = [r["e2e_s"] for r in rows if r["status"] == "ok" and r["e2e_s"] is not None]
        tps = [r["tokens_per_s"] for r in rows if r["status"] == "ok" and r["tokens_per_s"] is not None]
        statuses = [r["status"] for r in rows]
        unsupported = [r.get("reason") for r in rows if r["status"] == "unsupported"]
        errors = [r.get("error") for r in rows if r["status"] == "error"]
        first = rows[0]
        summaries.append(
            {
                "scenario_id": scenario_id,
                "stack": first["stack"],
                "model": first["model"],
                "mode": first["mode"],
                "thinking": first["thinking"],
                "cache_strategy": first["cache_strategy"],
                "prompt_type": first["prompt_type"],
                "samples": len(rows),
                "ok_count": statuses.count("ok"),
                "unsupported_count": statuses.count("unsupported"),
                "error_count": statuses.count("error"),
                "ttft_p50_s": percentile(ttfts, 50),
                "ttft_p95_s": percentile(ttfts, 95),
                "ttft_p99_s": percentile(ttfts, 99),
                "e2e_p50_s": percentile(e2es, 50),
                "e2e_p95_s": percentile(e2es, 95),
                "e2e_p99_s": percentile(e2es, 99),
                "tokens_per_s_avg": statistics.fmean(tps) if tps else None,
                "unsupported_reason_example": unsupported[0] if unsupported else None,
                "error_example": errors[0] if errors else None,
            }
        )
    summaries.sort(
        key=lambda row: (
            row["ttft_p50_s"] is None,
            row["ttft_p50_s"] if row["ttft_p50_s"] is not None else float("inf"),
        )
    )
    return summaries


def write_markdown_report(path: Path, summary_rows: List[Dict[str, Any]]) -> None:
    lines: List[str] = []
    lines.append("# Gemini TTFT Benchmark Report")
    lines.append("")
    lines.append(f"Generated at: `{utc_now_iso()}`")
    lines.append("")
    lines.append("## Fastest Scenarios By TTFT (P50)")
    lines.append("")
    lines.append("| Rank | Scenario | TTFT P50 (s) | E2E P50 (s) | Tokens/s Avg | Notes |")
    lines.append("| --- | --- | ---: | ---: | ---: | --- |")
    rank = 1
    for row in summary_rows[:10]:
        notes = []
        if row["unsupported_count"] > 0:
            notes.append(f"unsupported={row['unsupported_count']}")
        if row["error_count"] > 0:
            notes.append(f"errors={row['error_count']}")
        if not notes:
            notes.append("ok")
        lines.append(
            "| "
            + " | ".join(
                [
                    str(rank),
                    row["scenario_id"],
                    f"{row['ttft_p50_s']:.3f}" if row["ttft_p50_s"] is not None else "n/a",
                    f"{row['e2e_p50_s']:.3f}" if row["e2e_p50_s"] is not None else "n/a",
                    f"{row['tokens_per_s_avg']:.2f}" if row["tokens_per_s_avg"] is not None else "n/a",
                    ", ".join(notes),
                ]
            )
            + " |"
        )
        rank += 1
    lines.append("")
    lines.append("## Alternatives To Improve Response Speed")
    lines.append("")
    lines.append("- Use Flash models for latency-critical paths and route to Pro only on difficult prompts.")
    lines.append("- Prefer streaming so users see output as soon as the first chunk arrives.")
    lines.append("- Keep thinking disabled by default; enable it only when reasoning depth is needed.")
    lines.append("- Reuse long shared prefixes with implicit cache-like prompting or explicit cache APIs.")
    lines.append("- Pre-warm clients and avoid creating new SDK clients per request.")
    lines.append("- Reduce max output tokens and apply stop sequences for bounded completions.")
    lines.append("- Parallelize retrieval/tool calls before generation to reduce critical-path latency.")
    lines.append("- Keep prompts concise and move stable instructions into reusable templates.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def apply_cli_filters(scenarios: List[Scenario], args: argparse.Namespace) -> List[Scenario]:
    filtered = scenarios
    if args.models:
        allowed = {m.strip() for m in args.models.split(",") if m.strip()}
        filtered = [s for s in filtered if s.model in allowed]
    if args.stack:
        filtered = [s for s in filtered if s.stack == args.stack]
    if args.streaming_only:
        filtered = [s for s in filtered if s.mode == "streaming"]
    if args.trials is not None:
        filtered = [
            Scenario(
                stack=s.stack,
                model=s.model,
                mode=s.mode,
                thinking=s.thinking,
                cache_strategy=s.cache_strategy,
                prompt_type=s.prompt_type,
                trials=args.trials,
                warmup_trials=s.warmup_trials,
                max_output_tokens=s.max_output_tokens,
                temperature=s.temperature,
                timeout_s=s.timeout_s,
            )
            for s in filtered
        ]
    return filtered


def run_benchmark(config: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Path]:
    scenarios = apply_cli_filters(build_scenarios(config), args)
    run_id = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_root = Path(args.output_dir or config["output_dir"]) / run_id
    output_root.mkdir(parents=True, exist_ok=True)

    raw_rows: List[Dict[str, Any]] = []
    adapter_cache: Dict[str, Any] = {}

    for idx, scenario in enumerate(scenarios, start=1):
        print(f"[{idx}/{len(scenarios)}] Running {scenario.scenario_id}")
        prompt_cfg = config["prompts"][scenario.prompt_type]
        for iteration in range(scenario.warmup_trials + scenario.trials):
            is_warmup = iteration < scenario.warmup_trials
            status = "ok"
            payload: Dict[str, Any]
            started_at = utc_now_iso()
            try:
                if scenario.stack not in adapter_cache:
                    adapter_cache[scenario.stack] = adapter_for_scenario(scenario, config)
                adapter = adapter_cache[scenario.stack]
                payload = adapter.run_once(scenario, prompt_cfg)
            except Exception as exc:
                payload = {"status": "error", "error": f"{type(exc).__name__}: {exc}"}
            status = payload.get("status", "error")
            row = {
                "started_at": started_at,
                "scenario_id": scenario.scenario_id,
                "stack": scenario.stack,
                "model": scenario.model,
                "mode": scenario.mode,
                "thinking": scenario.thinking,
                "cache_strategy": scenario.cache_strategy,
                "prompt_type": scenario.prompt_type,
                "iteration": iteration,
                "is_warmup": is_warmup,
                "status": status,
                "ttft_s": payload.get("ttft_s"),
                "e2e_s": payload.get("e2e_s"),
                "output_tokens": payload.get("output_tokens"),
                "tokens_per_s": payload.get("tokens_per_s"),
                "reason": payload.get("reason"),
                "error": payload.get("error"),
                "response_preview": payload.get("response_preview"),
            }
            raw_rows.append(row)

    raw_jsonl = output_root / "raw_results.jsonl"
    write_jsonl(raw_jsonl, raw_rows)

    summary_rows = aggregate(raw_rows)
    summary_json = output_root / "summary.json"
    summary_json.write_text(json.dumps(summary_rows, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    summary_csv = output_root / "summary.csv"
    write_summary_csv(summary_csv, summary_rows)

    report_md = output_root / "report.md"
    write_markdown_report(report_md, summary_rows)

    return {
        "output_root": output_root,
        "raw_jsonl": raw_jsonl,
        "summary_json": summary_json,
        "summary_csv": summary_csv,
        "report_md": report_md,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gemini TTFT benchmark harness")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).with_name("benchmark_config.yaml"),
        help="Path to YAML benchmark config.",
    )
    parser.add_argument("--models", type=str, default=None, help="Comma-separated model list override.")
    parser.add_argument(
        "--stack",
        type=str,
        choices=["google_genai", "openai_compat"],
        default=None,
        help="Run only one stack.",
    )
    parser.add_argument("--trials", type=int, default=None, help="Override non-warmup trials per scenario.")
    parser.add_argument(
        "--streaming-only",
        action="store_true",
        help="Run only streaming scenarios.",
    )
    parser.add_argument("--output-dir", type=str, default=None, help="Custom output directory root.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    outputs = run_benchmark(config, args)
    print("\nBenchmark completed.")
    for key, value in outputs.items():
        print(f"- {key}: {value}")


if __name__ == "__main__":
    main()
