from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class OptimizerOutput:
    alternatives: List[str]
    trace: List[str]


class OptimizerAgent:
    def suggest(self, best_row: Optional[Dict[str, object]]) -> OptimizerOutput:
        alternatives = [
            "Use streaming for interactive UX so users see first token faster.",
            "Keep thinking disabled for routine requests; enable only for complex reasoning.",
            "Reuse stable context prefixes with implicit or explicit cache where supported.",
            "Set lower max_output_tokens for latency-critical endpoints.",
            "Use Google GenAI stack for full feature coverage and typically lower overhead.",
        ]
        trace = ["OptimizerAgent: generated latency-focused alternatives."]
        if best_row:
            trace.append(
                "OptimizerAgent: tuned suggestions around best scenario "
                f"{best_row.get('scenario_id')}."
            )
        return OptimizerOutput(alternatives=alternatives, trace=trace)

