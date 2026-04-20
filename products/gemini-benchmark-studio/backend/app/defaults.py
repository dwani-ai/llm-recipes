from typing import Dict, List


DEFAULT_STACKS: List[str] = ["google_genai", "openai_compat", "vertex_api"]
DEFAULT_MODELS: List[str] = ["gemini-2.5-flash", "gemini-2.5-pro"]
DEFAULT_PROMPT_TEMPLATE = (
    "Using {{dataset_name}}, produce a detailed, evidence-backed decision memo for {{goal}}. "
    "Return: (1) top findings, (2) trade-offs, (3) prioritized actions, and (4) measurable success criteria."
)


def best_mode_defaults() -> Dict[str, object]:
    return {
        "stack": "google_genai",
        "model": "gemini-2.5-flash",
        "streaming": False,
        "thinking": True,
        "thinking_token_budget": 256,
        "thinking_mode": "budget",
        "thinking_level": "medium",
        "implicit_cache": False,
        "explicit_cache": True,
        "trials": 10,
    }

