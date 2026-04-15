from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class ReporterOutput:
    rationale: str
    trace: List[str]


class ReporterAgent:
    def __init__(self) -> None:
        self._adk_available = False
        self._adk_error: Optional[str] = None
        self._initialize_adk()

    def _initialize_adk(self) -> None:
        try:
            __import__("google.adk")
            self._adk_available = True
        except Exception as exc:  # pragma: no cover
            self._adk_available = False
            self._adk_error = f"ADK unavailable ({type(exc).__name__})"

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
        if not self._adk_available:
            rationale = self._fallback_rationale(best_row)
            trace = [f"ReporterAgent: {self._adk_error or 'ADK unavailable'}; used fallback rationale."]
            return ReporterOutput(rationale=rationale, trace=trace)

        # In this implementation, ADK runtime is optional; fallback remains stable.
        rationale = self._fallback_rationale(best_row)
        trace = ["ReporterAgent: ADK module detected; using conservative local rationale formatter."]
        return ReporterOutput(rationale=rationale, trace=trace)

