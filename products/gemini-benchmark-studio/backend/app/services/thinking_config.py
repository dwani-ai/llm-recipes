from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class ThinkingCapabilities:
    supports_budget: bool
    supports_level: bool


def model_thinking_capabilities(model: str) -> ThinkingCapabilities:
    normalized = (model or "").lower()
    if normalized.startswith("gemini-3.1") or normalized.startswith("gemini-3"):
        return ThinkingCapabilities(supports_budget=False, supports_level=True)
    if normalized.startswith("gemini-2.5"):
        return ThinkingCapabilities(supports_budget=True, supports_level=False)
    # Conservative fallback for unknown models.
    return ThinkingCapabilities(supports_budget=True, supports_level=False)


def resolve_thinking_mode(
    model: str,
    thinking_enabled: bool,
    thinking_mode: str,
) -> str:
    if not thinking_enabled:
        return "off"
    if thinking_mode in {"budget", "level"}:
        return thinking_mode
    caps = model_thinking_capabilities(model)
    if caps.supports_level and not caps.supports_budget:
        return "level"
    return "budget"


def resolve_thinking_config(
    *,
    model: str,
    thinking_enabled: bool,
    thinking_mode: str,
    thinking_token_budget: int,
    thinking_level: Optional[str],
) -> Tuple[Optional[dict], Optional[str], str]:
    effective_mode = resolve_thinking_mode(model=model, thinking_enabled=thinking_enabled, thinking_mode=thinking_mode)
    if not thinking_enabled:
        return {"thinking_budget": 0}, None, effective_mode

    caps = model_thinking_capabilities(model)
    if effective_mode == "budget":
        if not caps.supports_budget:
            return None, "thinking_budget_not_supported_for_model", effective_mode
        if thinking_token_budget <= 0:
            return None, "thinking_budget_must_be_positive_when_thinking_enabled", effective_mode
        return {"thinking_budget": thinking_token_budget}, None, effective_mode

    if effective_mode == "level":
        if not caps.supports_level:
            return None, "thinking_level_not_supported_for_model", effective_mode
        level = (thinking_level or "medium").lower()
        if level not in {"minimal", "low", "medium", "high"}:
            return None, "invalid_thinking_level", effective_mode
        return {"thinking_level": level}, None, effective_mode

    return None, "invalid_thinking_mode", effective_mode
