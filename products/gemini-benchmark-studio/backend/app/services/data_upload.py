from typing import Tuple


MAX_CONTEXT_CHARS = 12000


def extract_context_from_bytes(content: bytes, filename: str) -> Tuple[str, int]:
    """
    Convert uploaded file bytes into text context suitable for prompt variables.
    Returns (context_text, original_size_bytes).
    """
    size_bytes = len(content)
    text = content.decode("utf-8", errors="replace")
    text = text.strip()
    if len(text) > MAX_CONTEXT_CHARS:
        suffix = f"\n\n[Truncated to first {MAX_CONTEXT_CHARS} chars from {filename}]"
        text = text[:MAX_CONTEXT_CHARS] + suffix
    return text, size_bytes

