from typing import Any, Callable, Dict, Optional


class ADKRuntime:
    """
    Minimal Google ADK bridge.

    If google-adk is installed and available, this class can be extended to
    execute richer multi-agent sessions. For v1, we keep a safe fallback path.
    """

    def __init__(self) -> None:
        self.available = False
        self.error: Optional[str] = None
        self.tools: Dict[str, Callable[..., Any]] = {}
        self._load()

    def _load(self) -> None:
        try:
            __import__("google.adk")
            self.available = True
        except Exception as exc:  # pragma: no cover
            self.available = False
            self.error = f"{type(exc).__name__}: {exc}"

    def summarize(self, prompt: str) -> Optional[str]:
        """
        Placeholder ADK call site.
        Return None to let caller use deterministic fallback text.
        """
        if not self.available:
            return None
        _ = prompt
        return None

    def register_tool(self, name: str, handler: Callable[..., Any]) -> None:
        self.tools[name] = handler

    def execute_tool(self, name: str, **kwargs: Any) -> Any:
        handler = self.tools.get(name)
        if handler is None:
            raise ValueError(f"Tool not found: {name}")
        return handler(**kwargs)

