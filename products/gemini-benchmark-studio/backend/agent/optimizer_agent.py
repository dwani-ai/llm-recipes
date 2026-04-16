from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class OptimizerOutput:
    alternatives: List[str]
    trace: List[str]


class OptimizerAgent:
    def suggest(
        self,
        best_row: Optional[Dict[str, object]],
        ranked_scenarios: List[Dict[str, object]],
        disqualified_scenarios: List[Dict[str, str]],
    ) -> OptimizerOutput:
        alternatives: List[str] = [
            "Set lower max_output_tokens for latency-critical endpoints.",
            "Use stable prompt templates and reuse long context only when needed.",
        ]
        if ranked_scenarios:
            top = ranked_scenarios[0]
            alternatives.append(
                f"Top ranked scenario is {top.get('scenario_id')} (score={top.get('score')}). "
                "Use it as your default and validate with production prompts."
            )
            if len(ranked_scenarios) > 1:
                runner_up = ranked_scenarios[1]
                alternatives.append(
                    f"Keep {runner_up.get('scenario_id')} as fallback; compare tail latency "
                    f"(TTFT P95 {runner_up.get('ttft_p95_s')}) before rollout."
                )
        if disqualified_scenarios:
            sampled = ", ".join(item["scenario_id"] for item in disqualified_scenarios[:2])
            alternatives.append(
                f"Disqualified scenarios ({sampled}) show low reliability; avoid them for production defaults."
            )
        if best_row and best_row.get("mode") == "non_streaming":
            alternatives.append("If UX is interactive, retest with streaming enabled to improve perceived latency.")
        if best_row and bool(best_row.get("thinking")):
            alternatives.append("If quality allows, disable thinking to reduce TTFT and improve consistency.")
        if best_row and best_row.get("cache_strategy") == "none":
            alternatives.append("For repeated long context requests, benchmark implicit reuse or explicit cache.")

        trace = ["OptimizerAgent: generated latency-focused alternatives."]
        if best_row:
            trace.append(
                "OptimizerAgent: tuned suggestions around best scenario "
                f"{best_row.get('scenario_id')}."
            )
        if disqualified_scenarios:
            trace.append(
                f"OptimizerAgent: considered {len(disqualified_scenarios)} disqualified scenarios."
            )
        return OptimizerOutput(alternatives=alternatives, trace=trace)

