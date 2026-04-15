from typing import Dict, List


DEFAULT_STACKS: List[str] = ["google_genai", "openai_compat", "vertex_api"]
DEFAULT_MODELS: List[str] = ["gemini-2.5-flash", "gemini-2.5-pro"]
DEFAULT_PROMPT_TEMPLATE = (
    "Analyze {{dataset_name}} for {{goal}}. "
    "Return concise latency-focused recommendations."
)


def best_mode_defaults() -> Dict[str, object]:
    return {
        "stack": "google_genai",
        "model": "gemini-2.5-flash",
        "streaming": True,
        "thinking": False,
        "implicit_cache": True,
        "explicit_cache": False,
        "trials": 10,
    }

