from dataclasses import dataclass
from typing import Dict, List, Optional

from agent.adk_runtime import ADKRuntime


@dataclass
class ReporterOutput:
    rationale: str
    trace: List[str]


class ReporterAgent:
    def __init__(self) -> None:
        self.adk_runtime = ADKRuntime()

    def _fallback_rationale(self, best_row: Optional[Dict[str, object]]) -> str:
        if best_row is None:
            return (
                "No successful benchmark scenario completed. "
                "Verify API key, network access, and selected mode compatibility."
            )
        return (
            f"Best scenario is {best_row.get('scenario_id')} with TTFT P50 "
            f"{best_row.get('ttft_p50_s'):.3f}s and E2E P50 {best_row.get('e2e_p50_s'):.3f}s."
        )

    def report(self, best_row: Optional[Dict[str, object]], summaries: List[Dict[str, object]]) -> ReporterOutput:
        adk_prompt = (
            "Summarize benchmark recommendation with emphasis on TTFT and reliability. "
            f"Best row: {best_row}. Total summaries: {len(summaries)}"
        )
        adk_summary = self.adk_runtime.summarize(adk_prompt)
        if not self.adk_runtime.available or adk_summary is None:
            rationale = self._fallback_rationale(best_row)
            trace = [
                "ReporterAgent: ADK summary unavailable; used deterministic fallback rationale."
            ]
            return ReporterOutput(rationale=rationale, trace=trace)

        rationale = adk_summary
        trace = ["ReporterAgent: ADK runtime generated rationale."]
        return ReporterOutput(rationale=rationale, trace=trace)

