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
        ttft = best_row.get("ttft_p50_s")
        e2e = best_row.get("e2e_p50_s")
        ttft_text = f"{float(ttft):.3f}s" if isinstance(ttft, (int, float)) else "n/a"
        e2e_text = f"{float(e2e):.3f}s" if isinstance(e2e, (int, float)) else "n/a"
        return (
            f"Best scenario is {best_row.get('scenario_id')} with TTFT P50 "
            f"{ttft_text} and E2E P50 {e2e_text}."
        )

    def report(
        self,
        best_row: Optional[Dict[str, object]],
        summaries: List[Dict[str, object]],
        ranked_scenarios: List[Dict[str, object]],
        confidence: str,
        reliability_score: float,
        objective: str,
    ) -> ReporterOutput:
        runner_up = ranked_scenarios[1] if len(ranked_scenarios) > 1 else None
        adk_prompt = (
            "Summarize benchmark recommendation with emphasis on TTFT and reliability.\n"
            f"Objective: {objective}\n"
            f"Best row: {best_row}\n"
            f"Runner up: {runner_up}\n"
            f"Confidence: {confidence}, reliability_score={reliability_score}\n"
            f"Total summaries: {len(summaries)}"
        )
        adk_summary = self.adk_runtime.summarize(adk_prompt)
        if not self.adk_runtime.available or adk_summary is None:
            rationale = self._fallback_rationale(best_row)
            if best_row and runner_up:
                ttft_delta = (runner_up.get("ttft_p50_s") or 0.0) - (best_row.get("ttft_p50_s") or 0.0)
                rationale += f" It beats runner-up by {ttft_delta:.3f}s on TTFT P50."
            rationale += f" Confidence={confidence}, reliability score={reliability_score:.3f}."
            trace = [
                "ReporterAgent: ADK summary unavailable; used deterministic fallback rationale."
            ]
            return ReporterOutput(rationale=rationale, trace=trace)

        rationale = adk_summary
        trace = ["ReporterAgent: ADK runtime generated rationale."]
        return ReporterOutput(rationale=rationale, trace=trace)

