from typing import Any, Dict, List, Optional

from app.schemas import ModeSelection, VertexConfig


class TokenCountError(RuntimeError):
    pass


def _extract_total_tokens(response: Any) -> Optional[int]:
    for attr in ("total_tokens", "total_token_count"):
        value = getattr(response, attr, None)
        if isinstance(value, int):
            return value
    if isinstance(response, dict):
        for key in ("total_tokens", "total_token_count"):
            value = response.get(key)
            if isinstance(value, int):
                return value
    return None


def count_tokens_exact(
    stack: str,
    model: str,
    prompt_text: str,
    api_key: Optional[str],
    vertex_config: Optional[VertexConfig],
) -> int:
    if not prompt_text.strip():
        return 0
    try:
        from google import genai
    except ImportError as exc:
        raise TokenCountError("google-genai is required for exact token count.") from exc

    if stack in {"google_genai", "openai_compat"}:
        if not api_key:
            raise TokenCountError("api_key is required for exact token counting on this stack.")
        client = genai.Client(api_key=api_key)
    elif stack == "vertex_api":
        if vertex_config is None:
            raise TokenCountError("vertex_config is required for exact token counting on vertex_api.")
        # Uses ADC for Vertex auth; access_token path is not used by this SDK call.
        client = genai.Client(vertexai=True, project=vertex_config.project_id, location=vertex_config.location)
    else:
        raise TokenCountError(f"Unsupported stack for exact token counting: {stack}")

    try:
        response = client.models.count_tokens(
            model=model,
            contents=[{"role": "user", "parts": [{"text": prompt_text}]}],
        )
    except Exception as exc:  # pragma: no cover
        raise TokenCountError(f"Token count failed: {type(exc).__name__}: {exc}") from exc

    token_count = _extract_total_tokens(response)
    if token_count is None:
        raise TokenCountError("Could not read total token count from provider response.")
    return token_count


def _build_prompt_configs(rendered_prompt: str, prompt_variables: Dict[str, str]) -> Dict[str, Dict[str, str]]:
    context_blob = (prompt_variables.get("data_context") or "").strip()
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


def mode_aware_token_breakdown(
    stack: str,
    model: str,
    api_key: Optional[str],
    vertex_config: Optional[VertexConfig],
    rendered_prompt: str,
    prompt_variables: Dict[str, str],
    mode_selection: ModeSelection,
    include_long_context: bool,
    calls_for_savings: int,
) -> Dict[str, Any]:
    prompt_cfg = _build_prompt_configs(rendered_prompt, prompt_variables)
    prompt_types: List[str] = ["short_prompt", "long_context"] if include_long_context else ["short_prompt"]
    strategies: List[str] = ["none"]
    if mode_selection.implicit_cache:
        strategies.append("implicit_reuse")
    if mode_selection.explicit_cache:
        strategies.append("explicit_cache")

    breakdown: List[Dict[str, Any]] = []
    for prompt_type in prompt_types:
        user_prompt = prompt_cfg[prompt_type]["user"].strip()
        shared_prefix = prompt_cfg[prompt_type]["shared_prefix"].strip()
        baseline_tokens = count_tokens_exact(stack, model, user_prompt, api_key, vertex_config)

        for strategy in strategies:
            if strategy == "none":
                request_prompt = user_prompt
                request_tokens = baseline_tokens
                cache_create_tokens = 0
            else:
                request_prompt = f"{shared_prefix}\n{user_prompt}".strip()
                request_tokens = count_tokens_exact(stack, model, request_prompt, api_key, vertex_config)
                cache_create_tokens = (
                    count_tokens_exact(stack, model, shared_prefix, api_key, vertex_config)
                    if strategy == "explicit_cache"
                    else 0
                )

            first_total = request_tokens + cache_create_tokens
            subsequent = request_tokens
            baseline_total_n = baseline_tokens * calls_for_savings
            strategy_total_n = first_total + (subsequent * max(calls_for_savings - 1, 0))
            savings = baseline_total_n - strategy_total_n

            breakdown.append(
                {
                    "prompt_type": prompt_type,
                    "strategy": strategy,
                    "baseline_request_tokens": baseline_tokens,
                    "request_tokens": request_tokens,
                    "cache_create_tokens": cache_create_tokens,
                    "first_call_total_tokens": first_total,
                    "subsequent_call_tokens": subsequent,
                    "savings_vs_baseline_after_n_calls": savings,
                }
            )

    # Primary count for backwards compatibility: short prompt + selected strongest strategy
    primary_strategy = (
        "explicit_cache"
        if mode_selection.explicit_cache
        else ("implicit_reuse" if mode_selection.implicit_cache else "none")
    )
    primary_match = next(
        (
            item
            for item in breakdown
            if item["prompt_type"] == "short_prompt" and item["strategy"] == primary_strategy
        ),
        None,
    )
    token_count = primary_match["request_tokens"] if primary_match else 0
    return {"token_count": token_count, "breakdown": breakdown}

