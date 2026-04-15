import csv
import itertools
import json
import statistics
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from app.schemas import BenchmarkRequest


def utc_now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def percentile(values: List[float], p: float) -> Optional[float]:
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    values = sorted(values)
    index = (len(values) - 1) * (p / 100.0)
    lower = int(index)
    upper = min(lower + 1, len(values) - 1)
    if lower == upper:
        return values[lower]
    weight = index - lower
    return values[lower] * (1.0 - weight) + values[upper] * weight


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, len(text.split()))


def normalize_text(parts: Iterable[str]) -> str:
    return "".join(p for p in parts if p)


@dataclass(frozen=True)
class Scenario:
    stack: str
    model: str
    mode: str
    thinking: bool
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


class GoogleGenAIAdapter:
    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise RuntimeError("api_key is required for google_genai stack.")
        try:
            from google import genai
        except ImportError as exc:
            raise RuntimeError("google-genai is not installed.") from exc
        self.client = genai.Client(api_key=api_key)
        self.cache_by_key: Dict[Tuple[str, str], str] = {}

    def _config(self, scenario: Scenario, explicit_cache_name: Optional[str]) -> Dict[str, Any]:
        cfg: Dict[str, Any] = {
            "max_output_tokens": scenario.max_output_tokens,
            "temperature": scenario.temperature,
        }
        if scenario.thinking:
            cfg["thinking_config"] = {"thinking_budget": 1024}
        else:
            cfg["thinking_config"] = {"thinking_budget": 0}
        if explicit_cache_name:
            cfg["cached_content"] = explicit_cache_name
        return cfg

    def _ensure_explicit_cache(self, scenario: Scenario, prompt_cfg: Dict[str, str]) -> Tuple[Optional[str], Optional[str]]:
        key = (scenario.model, scenario.prompt_type)
        if key in self.cache_by_key:
            return self.cache_by_key[key], None
        if not hasattr(self.client, "caches"):
            return None, "google_genai_cache_api_not_available"
        shared_prefix = prompt_cfg.get("shared_prefix", "").strip()
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
        except Exception as exc:  # pragma: no cover
            return None, f"explicit_cache_create_failed:{type(exc).__name__}"
        cache_name = getattr(cache_obj, "name", None)
        if not cache_name:
            return None, "explicit_cache_created_without_name"
        self.cache_by_key[key] = cache_name
        return cache_name, None

    def run_once(self, scenario: Scenario, prompt_cfg: Dict[str, str]) -> Dict[str, Any]:
        explicit_cache_name = None
        if scenario.cache_strategy == "explicit_cache":
            explicit_cache_name, cache_error = self._ensure_explicit_cache(scenario, prompt_cfg)
            if cache_error:
                return {"status": "unsupported", "reason": cache_error}

        prompt = prompt_cfg["user"] if scenario.cache_strategy == "none" else f"{prompt_cfg['shared_prefix']}\n{prompt_cfg['user']}"
        contents = [{"role": "user", "parts": [{"text": prompt.strip()}]}]
        config = self._config(scenario, explicit_cache_name)
        if scenario.mode == "streaming":
            return self._streaming(scenario, contents, config)
        return self._non_streaming(scenario, contents, config)

    def _streaming(self, scenario: Scenario, contents: List[Dict[str, Any]], config: Dict[str, Any]) -> Dict[str, Any]:
        start = time.perf_counter()
        first_chunk: Optional[float] = None
        parts: List[str] = []
        try:
            stream = self.client.models.generate_content_stream(
                model=scenario.model,
                contents=contents,
                config=config,
            )
            for chunk in stream:
                if first_chunk is None:
                    first_chunk = time.perf_counter()
                parts.append(getattr(chunk, "text", "") or "")
            end = time.perf_counter()
        except Exception as exc:  # pragma: no cover
            return {"status": "error", "error": f"{type(exc).__name__}: {exc}"}
        text = normalize_text(parts)
        total = end - start
        ttft = (first_chunk - start) if first_chunk else total
        tokens = estimate_tokens(text)
        return {
            "status": "ok",
            "ttft_s": ttft,
            "e2e_s": total,
            "output_tokens": tokens,
            "tokens_per_s": (tokens / total) if total > 0 else None,
        }

    def _non_streaming(self, scenario: Scenario, contents: List[Dict[str, Any]], config: Dict[str, Any]) -> Dict[str, Any]:
        start = time.perf_counter()
        try:
            response = self.client.models.generate_content(
                model=scenario.model,
                contents=contents,
                config=config,
            )
            end = time.perf_counter()
        except Exception as exc:  # pragma: no cover
            return {"status": "error", "error": f"{type(exc).__name__}: {exc}"}
        text = getattr(response, "text", "") or ""
        total = end - start
        tokens = estimate_tokens(text)
        return {
            "status": "ok",
            "ttft_s": total,
            "e2e_s": total,
            "output_tokens": tokens,
            "tokens_per_s": (tokens / total) if total > 0 else None,
        }


class OpenAICompatAdapter:
    def __init__(self, api_key: str, base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/") -> None:
        if not api_key:
            raise RuntimeError("api_key is required for openai_compat stack.")
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("openai package is not installed.") from exc
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def run_once(self, scenario: Scenario, prompt_cfg: Dict[str, str]) -> Dict[str, Any]:
        if scenario.cache_strategy == "explicit_cache":
            return {"status": "unsupported", "reason": "explicit_cache_not_supported_openai_compat"}
        if scenario.thinking:
            return {"status": "unsupported", "reason": "thinking_toggle_not_supported_openai_compat"}
        prompt = prompt_cfg["user"] if scenario.cache_strategy == "none" else f"{prompt_cfg['shared_prefix']}\n{prompt_cfg['user']}"
        messages = [{"role": "user", "content": prompt.strip()}]
        if scenario.mode == "streaming":
            return self._streaming(scenario, messages)
        return self._non_streaming(scenario, messages)

    def _streaming(self, scenario: Scenario, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        start = time.perf_counter()
        first_chunk: Optional[float] = None
        parts: List[str] = []
        try:
            stream = self.client.chat.completions.create(
                model=scenario.model,
                messages=messages,
                max_tokens=scenario.max_output_tokens,
                temperature=scenario.temperature,
                timeout=scenario.timeout_s,
                stream=True,
            )
            for chunk in stream:
                if first_chunk is None:
                    first_chunk = time.perf_counter()
                delta = chunk.choices[0].delta
                parts.append(getattr(delta, "content", "") or "")
            end = time.perf_counter()
        except Exception as exc:  # pragma: no cover
            return {"status": "error", "error": f"{type(exc).__name__}: {exc}"}
        text = normalize_text(parts)
        total = end - start
        ttft = (first_chunk - start) if first_chunk else total
        tokens = estimate_tokens(text)
        return {
            "status": "ok",
            "ttft_s": ttft,
            "e2e_s": total,
            "output_tokens": tokens,
            "tokens_per_s": (tokens / total) if total > 0 else None,
        }

    def _non_streaming(self, scenario: Scenario, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        start = time.perf_counter()
        try:
            response = self.client.chat.completions.create(
                model=scenario.model,
                messages=messages,
                max_tokens=scenario.max_output_tokens,
                temperature=scenario.temperature,
                timeout=scenario.timeout_s,
                stream=False,
            )
            end = time.perf_counter()
        except Exception as exc:  # pragma: no cover
            return {"status": "error", "error": f"{type(exc).__name__}: {exc}"}
        text = response.choices[0].message.content or ""
        total = end - start
        tokens = estimate_tokens(text)
        return {
            "status": "ok",
            "ttft_s": total,
            "e2e_s": total,
            "output_tokens": tokens,
            "tokens_per_s": (tokens / total) if total > 0 else None,
        }


class VertexAPIAdapter(OpenAICompatAdapter):
    def __init__(self, project_id: str, location: str, endpoint_id: str, access_token: Optional[str] = None) -> None:
        token = access_token or self._fetch_adc_token()
        base_url = (
            f"https://{location}-aiplatform.googleapis.com/v1/projects/{project_id}/"
            f"locations/{location}/endpoints/{endpoint_id}"
        )
        super().__init__(api_key=token, base_url=base_url)

    @staticmethod
    def _fetch_adc_token() -> str:
        try:
            from google.auth import default
            from google.auth.transport.requests import Request
        except ImportError as exc:
            raise RuntimeError(
                "google-auth is required for Vertex ADC token fallback."
            ) from exc
        credentials, _ = default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        credentials.refresh(Request())
        token = getattr(credentials, "token", None)
        if not token:
            raise RuntimeError("Unable to obtain ADC access token for Vertex API.")
        return token


class BenchmarkRunner:
    def __init__(self, output_root: Optional[Path] = None) -> None:
        base = output_root or (Path(__file__).resolve().parents[2] / "outputs" / "gemini_ttft")
        self.output_root = base

    def build_scenarios(self, request: BenchmarkRequest) -> List[Scenario]:
        modes = ["streaming"] if request.mode_selection.streaming else ["non_streaming"]
        thinking_values = [True] if request.mode_selection.thinking else [False]
        cache_values = ["none"]
        if request.mode_selection.implicit_cache:
            cache_values.append("implicit_reuse")
        if request.mode_selection.explicit_cache:
            cache_values.append("explicit_cache")
        prompt_types = ["short_prompt", "long_context"] if request.include_long_context else ["short_prompt"]
        scenarios: List[Scenario] = []
        for stack, model, mode, thinking, cache, prompt_type in itertools.product(
            request.stacks,
            request.models,
            modes,
            thinking_values,
            cache_values,
            prompt_types,
        ):
            scenarios.append(
                Scenario(
                    stack=stack,
                    model=model,
                    mode=mode,
                    thinking=thinking,
                    cache_strategy=cache,
                    prompt_type=prompt_type,
                    trials=request.trials,
                    warmup_trials=request.warmup_trials,
                    max_output_tokens=request.max_output_tokens,
                    temperature=request.temperature,
                    timeout_s=request.timeout_s,
                )
            )
        return scenarios

    def _prompt_configs(self, rendered_prompt: str, prompt_variables: Dict[str, str]) -> Dict[str, Dict[str, str]]:
        context_blob = prompt_variables.get("data_context", "").strip()
        if not context_blob:
            context_blob = "User data context was not provided."
        long_prefix = (
            "Dataset context:\n"
            f"{context_blob}\n\n"
            "Benchmark objective:\n"
            "Measure TTFT and end-to-end latency across selected modes."
        )
        return {
            "short_prompt": {"user": rendered_prompt, "shared_prefix": context_blob},
            "long_context": {"user": rendered_prompt, "shared_prefix": long_prefix},
        }

    def _write_jsonl(self, path: Path, rows: Iterable[Dict[str, Any]]) -> None:
        with path.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=True) + "\n")

    def _write_csv(self, path: Path, rows: List[Dict[str, Any]]) -> None:
        if not rows:
            path.write_text("", encoding="utf-8")
            return
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    def _aggregate(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for row in rows:
            if row["is_warmup"]:
                continue
            grouped.setdefault(row["scenario_id"], []).append(row)
        summaries: List[Dict[str, Any]] = []
        for scenario_id, items in grouped.items():
            ttfts = [item["ttft_s"] for item in items if item["status"] == "ok" and item["ttft_s"] is not None]
            e2es = [item["e2e_s"] for item in items if item["status"] == "ok" and item["e2e_s"] is not None]
            tps = [
                item["tokens_per_s"]
                for item in items
                if item["status"] == "ok" and item["tokens_per_s"] is not None
            ]
            first = items[0]
            statuses = [item["status"] for item in items]
            unsupported = [item.get("reason") for item in items if item["status"] == "unsupported"]
            errors = [item.get("error") for item in items if item["status"] == "error"]
            summaries.append(
                {
                    "scenario_id": scenario_id,
                    "stack": first["stack"],
                    "model": first["model"],
                    "mode": first["mode"],
                    "thinking": first["thinking"],
                    "cache_strategy": first["cache_strategy"],
                    "prompt_type": first["prompt_type"],
                    "samples": len(items),
                    "ok_count": statuses.count("ok"),
                    "unsupported_count": statuses.count("unsupported"),
                    "error_count": statuses.count("error"),
                    "ttft_p50_s": percentile(ttfts, 50),
                    "ttft_p95_s": percentile(ttfts, 95),
                    "e2e_p50_s": percentile(e2es, 50),
                    "tokens_per_s_avg": statistics.fmean(tps) if tps else None,
                    "note": unsupported[0] if unsupported else (errors[0] if errors else None),
                }
            )
        summaries.sort(key=lambda x: (x["ttft_p50_s"] is None, x["ttft_p50_s"] or 1e9))
        return summaries

    def _write_report(self, path: Path, summary_rows: List[Dict[str, Any]]) -> None:
        lines = [
            "# Gemini TTFT Benchmark Report",
            "",
            f"Generated at: `{utc_now_iso()}`",
            "",
            "## Fastest Scenarios By TTFT (P50)",
            "",
            "| Rank | Scenario | TTFT P50 (s) | E2E P50 (s) | Tokens/s Avg | Notes |",
            "| --- | --- | ---: | ---: | ---: | --- |",
        ]
        for idx, row in enumerate(summary_rows[:10], start=1):
            note = "ok"
            if row["error_count"] > 0:
                note = f"errors={row['error_count']}"
            elif row["unsupported_count"] > 0:
                note = f"unsupported={row['unsupported_count']}"
            ttft = f"{row['ttft_p50_s']:.3f}" if row["ttft_p50_s"] is not None else "n/a"
            e2e = f"{row['e2e_p50_s']:.3f}" if row["e2e_p50_s"] is not None else "n/a"
            tps = f"{row['tokens_per_s_avg']:.2f}" if row["tokens_per_s_avg"] is not None else "n/a"
            lines.append(f"| {idx} | {row['scenario_id']} | {ttft} | {e2e} | {tps} | {note} |")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def run(self, request: BenchmarkRequest, rendered_prompt: str) -> Dict[str, Any]:
        run_id = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        run_dir = self.output_root / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        scenarios = self.build_scenarios(request)
        prompts = self._prompt_configs(rendered_prompt, request.prompt_variables)

        adapters: Dict[str, Any] = {}
        if "google_genai" in request.stacks:
            try:
                adapters["google_genai"] = GoogleGenAIAdapter(request.api_key or "")
            except Exception as exc:
                adapters["google_genai"] = {"init_error": f"{type(exc).__name__}: {exc}"}
        if "openai_compat" in request.stacks:
            try:
                adapters["openai_compat"] = OpenAICompatAdapter(request.api_key or "")
            except Exception as exc:
                adapters["openai_compat"] = {"init_error": f"{type(exc).__name__}: {exc}"}
        if "vertex_api" in request.stacks:
            if request.vertex_config is None:
                adapters["vertex_api"] = {"init_error": "vertex_config is required for vertex_api stack."}
            else:
                try:
                    adapters["vertex_api"] = VertexAPIAdapter(
                        project_id=request.vertex_config.project_id,
                        location=request.vertex_config.location,
                        endpoint_id=request.vertex_config.endpoint_id,
                        access_token=request.vertex_config.access_token,
                    )
                except Exception as exc:
                    adapters["vertex_api"] = {"init_error": f"{type(exc).__name__}: {exc}"}

        raw_rows: List[Dict[str, Any]] = []
        for scenario in scenarios:
            if scenario.stack not in adapters:
                raw_rows.append(
                    {
                        "started_at": utc_now_iso(),
                        "scenario_id": scenario.scenario_id,
                        "stack": scenario.stack,
                        "model": scenario.model,
                        "mode": scenario.mode,
                        "thinking": scenario.thinking,
                        "cache_strategy": scenario.cache_strategy,
                        "prompt_type": scenario.prompt_type,
                        "iteration": 0,
                        "is_warmup": False,
                        "status": "unsupported",
                        "ttft_s": None,
                        "e2e_s": None,
                        "output_tokens": None,
                        "tokens_per_s": None,
                        "reason": f"unsupported_stack:{scenario.stack}",
                        "error": None,
                    }
                )
                continue
            adapter = adapters[scenario.stack]
            if isinstance(adapter, dict) and adapter.get("init_error"):
                raw_rows.append(
                    {
                        "started_at": utc_now_iso(),
                        "scenario_id": scenario.scenario_id,
                        "stack": scenario.stack,
                        "model": scenario.model,
                        "mode": scenario.mode,
                        "thinking": scenario.thinking,
                        "cache_strategy": scenario.cache_strategy,
                        "prompt_type": scenario.prompt_type,
                        "iteration": 0,
                        "is_warmup": False,
                        "status": "error",
                        "ttft_s": None,
                        "e2e_s": None,
                        "output_tokens": None,
                        "tokens_per_s": None,
                        "reason": None,
                        "error": adapter["init_error"],
                    }
                )
                continue
            prompt_cfg = prompts[scenario.prompt_type]
            for iteration in range(scenario.warmup_trials + scenario.trials):
                is_warmup = iteration < scenario.warmup_trials
                payload = adapter.run_once(scenario, prompt_cfg)
                raw_rows.append(
                    {
                        "started_at": utc_now_iso(),
                        "scenario_id": scenario.scenario_id,
                        "stack": scenario.stack,
                        "model": scenario.model,
                        "mode": scenario.mode,
                        "thinking": scenario.thinking,
                        "cache_strategy": scenario.cache_strategy,
                        "prompt_type": scenario.prompt_type,
                        "iteration": iteration,
                        "is_warmup": is_warmup,
                        "status": payload.get("status", "error"),
                        "ttft_s": payload.get("ttft_s"),
                        "e2e_s": payload.get("e2e_s"),
                        "output_tokens": payload.get("output_tokens"),
                        "tokens_per_s": payload.get("tokens_per_s"),
                        "reason": payload.get("reason"),
                        "error": payload.get("error"),
                    }
                )

        raw_path = run_dir / "raw_results.jsonl"
        self._write_jsonl(raw_path, raw_rows)

        summaries = self._aggregate(raw_rows)
        summary_json = run_dir / "summary.json"
        summary_json.write_text(json.dumps(summaries, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

        summary_csv = run_dir / "summary.csv"
        self._write_csv(summary_csv, summaries)

        report_md = run_dir / "report.md"
        self._write_report(report_md, summaries)

        return {
            "run_id": run_id,
            "summaries": summaries,
            "artifacts": {
                "output_root": str(run_dir),
                "raw_jsonl": str(raw_path),
                "summary_json": str(summary_json),
                "summary_csv": str(summary_csv),
                "report_md": str(report_md),
            },
        }

