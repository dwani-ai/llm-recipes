from dataclasses import dataclass
from typing import Any, Dict, List

from agent.adk_runtime import ADKRuntime


@dataclass
class ToolWorkerOutput:
    outputs: Dict[str, Any]
    trace: List[str]


class ToolWorkerAgent:
    """
    Executes tool-calling style tasks through ADKRuntime hook registry.
    """

    def __init__(self, runtime: ADKRuntime) -> None:
        self.runtime = runtime

    def run(self, requests: List[Dict[str, Any]]) -> ToolWorkerOutput:
        outputs: Dict[str, Any] = {}
        trace: List[str] = []
        for item in requests:
            tool_name = item.get("tool")
            kwargs = item.get("kwargs", {})
            key = item.get("output_key", tool_name)
            if not tool_name:
                continue
            try:
                outputs[key] = self.runtime.execute_tool(tool_name, **kwargs)
                trace.append(f"ToolWorkerAgent: executed tool '{tool_name}'.")
            except Exception as exc:
                outputs[key] = {"error": f"{type(exc).__name__}: {exc}"}
                trace.append(f"ToolWorkerAgent: tool '{tool_name}' failed.")
        return ToolWorkerOutput(outputs=outputs, trace=trace)

