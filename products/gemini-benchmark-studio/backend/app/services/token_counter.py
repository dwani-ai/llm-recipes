from typing import Any, Dict, Optional

from app.schemas import VertexConfig


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

