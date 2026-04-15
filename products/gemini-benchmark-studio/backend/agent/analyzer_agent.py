from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class AnalyzerOutput:
    best_scenario_id: Optional[str]
    best_row: Optional[Dict[str, Any]]
    trace: List[str]


class AnalyzerAgent:
    def analyze(self, summaries: List[Dict[str, Any]]) -> AnalyzerOutput:
        ok_rows = [row for row in summaries if row.get("ok_count", 0) > 0 and row.get("ttft_p50_s") is not None]
        if not ok_rows:
            return AnalyzerOutput(
                best_scenario_id=None,
                best_row=None,
                trace=["AnalyzerAgent: no successful scenario found; returning fallback path."],
            )
        best = sorted(ok_rows, key=lambda row: row["ttft_p50_s"])[0]
        return AnalyzerOutput(
            best_scenario_id=best["scenario_id"],
            best_row=best,
            trace=[
                f"AnalyzerAgent: evaluated {len(ok_rows)} successful scenarios.",
                f"AnalyzerAgent: selected {best['scenario_id']} as lowest TTFT.",
            ],
        )

