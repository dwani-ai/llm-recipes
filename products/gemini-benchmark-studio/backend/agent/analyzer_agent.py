from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class AnalyzerOutput:
    best_scenario_id: Optional[str]
    best_row: Optional[Dict[str, Any]]
    ranked_scenarios: List[Dict[str, Any]]
    disqualified_scenarios: List[Dict[str, str]]
    reliability_score: float
    confidence: str
    gate_pass_count: int
    gate_fail_count: int
    overall_acceptance_status: str
    trace: List[str]


class AnalyzerAgent:
    def _objective_weights(self, objective: str) -> Tuple[float, float, float, float]:
        if objective == "reliability_first":
            return 0.30, 0.15, 0.10, 0.45
        if objective == "balanced":
            return 0.45, 0.20, 0.20, 0.15
        return 0.65, 0.20, 0.15, 0.00

    def _latency_component(
        self, value: Optional[float], min_value: float, max_value: float, default: float = 0.0
    ) -> float:
        if value is None:
            return default
        if max_value == min_value:
            return 1.0
        # Lower latency is better.
        return max(0.0, 1.0 - ((value - min_value) / (max_value - min_value)))

    def _confidence_label(self, eligible_count: int, reliability_score: float) -> str:
        if eligible_count == 0:
            return "low"
        if eligible_count >= 3 and reliability_score >= 0.8:
            return "high"
        if reliability_score >= 0.6:
            return "medium"
        return "low"

    def analyze(
        self,
        summaries: List[Dict[str, Any]],
        objective: str = "lowest_latency",
        acceptance_tier: str = "standard",
        tier_thresholds: Optional[Dict[str, Dict[str, Any]]] = None,
        evaluation_enabled: bool = False,
    ) -> AnalyzerOutput:
        trace: List[str] = []
        eligible: List[Dict[str, Any]] = []
        disqualified: List[Dict[str, str]] = []
        gate_pass_count = 0
        gate_fail_count = 0

        tier_cfg = (tier_thresholds or {}).get(acceptance_tier, {})
        min_accuracy = float(tier_cfg.get("min_accuracy_score", 0.0))
        max_ttft = tier_cfg.get("max_ttft_p50_s")

        for row in summaries:
            samples = int(row.get("samples", 0) or 0)
            ok_count = int(row.get("ok_count", 0) or 0)
            unsupported_count = int(row.get("unsupported_count", 0) or 0)
            error_count = int(row.get("error_count", 0) or 0)
            success_rate = (ok_count / samples) if samples > 0 else 0.0

            if ok_count <= 0:
                reason = "no_successful_trials"
            elif row.get("ttft_p50_s") is None:
                reason = "missing_ttft_metric"
            elif success_rate < 0.60:
                reason = "low_success_rate"
            elif unsupported_count > ok_count:
                reason = "mostly_unsupported"
            elif max_ttft is not None and row.get("ttft_p50_s") is not None and row.get("ttft_p50_s") > max_ttft:
                reason = "failed_latency_gate_for_tier"
            elif evaluation_enabled and row.get("accuracy_score") is None:
                reason = "evaluation_unavailable"
            elif evaluation_enabled and float(row.get("accuracy_score") or 0.0) < min_accuracy:
                reason = "failed_accuracy_gate"
            else:
                reason = ""

            if reason:
                row["acceptance_tier"] = acceptance_tier
                row["acceptance_passed"] = False
                row["acceptance_reason"] = reason
                disqualified.append({"scenario_id": row["scenario_id"], "reason": reason})
                gate_fail_count += 1
                continue

            row["acceptance_tier"] = acceptance_tier
            row["acceptance_passed"] = True
            row["acceptance_reason"] = "passed"
            gate_pass_count += 1
            reliability = max(0.0, min(1.0, success_rate - ((error_count / samples) if samples > 0 else 0.0)))
            eligible.append(
                {
                    "row": row,
                    "success_rate": success_rate,
                    "error_rate": (error_count / samples) if samples > 0 else 0.0,
                    "unsupported_rate": (unsupported_count / samples) if samples > 0 else 0.0,
                    "reliability": reliability,
                }
            )

        if not eligible:
            return AnalyzerOutput(
                best_scenario_id=None,
                best_row=None,
                ranked_scenarios=[],
                disqualified_scenarios=disqualified,
                reliability_score=0.0,
                confidence="low",
                gate_pass_count=gate_pass_count,
                gate_fail_count=gate_fail_count,
                overall_acceptance_status="failed" if gate_fail_count > 0 else "unknown",
                trace=["AnalyzerAgent: no eligible scenario found after reliability gating."],
            )

        ttft_values = [entry["row"].get("ttft_p50_s") for entry in eligible if entry["row"].get("ttft_p50_s") is not None]
        p95_values = [entry["row"].get("ttft_p95_s") for entry in eligible if entry["row"].get("ttft_p95_s") is not None]
        e2e_values = [entry["row"].get("e2e_p50_s") for entry in eligible if entry["row"].get("e2e_p50_s") is not None]

        min_ttft, max_ttft = min(ttft_values), max(ttft_values)
        min_p95, max_p95 = (min(p95_values), max(p95_values)) if p95_values else (0.0, 1.0)
        min_e2e, max_e2e = (min(e2e_values), max(e2e_values)) if e2e_values else (0.0, 1.0)
        w_ttft, w_p95, w_e2e, w_rel = self._objective_weights(objective)

        ranked: List[Dict[str, Any]] = []
        for entry in eligible:
            row = entry["row"]
            score = (
                w_ttft * self._latency_component(row.get("ttft_p50_s"), min_ttft, max_ttft)
                + w_p95 * self._latency_component(row.get("ttft_p95_s"), min_p95, max_p95, default=0.5)
                + w_e2e * self._latency_component(row.get("e2e_p50_s"), min_e2e, max_e2e, default=0.5)
                + w_rel * entry["reliability"]
            )
            ranked.append(
                {
                    "scenario_id": row["scenario_id"],
                    "score": round(score, 4),
                    "ttft_p50_s": row.get("ttft_p50_s"),
                    "ttft_p95_s": row.get("ttft_p95_s"),
                    "e2e_p50_s": row.get("e2e_p50_s"),
                    "tokens_per_s_avg": row.get("tokens_per_s_avg"),
                    "accuracy_score": row.get("accuracy_score"),
                    "success_rate": round(entry["success_rate"], 3),
                    "error_rate": round(entry["error_rate"], 3),
                    "unsupported_rate": round(entry["unsupported_rate"], 3),
                }
            )

        ranked.sort(key=lambda item: item["score"], reverse=True)
        best_id = ranked[0]["scenario_id"]
        best_row = next(entry["row"] for entry in eligible if entry["row"]["scenario_id"] == best_id)
        reliability_score = round(sum(entry["reliability"] for entry in eligible) / len(eligible), 3)
        confidence = self._confidence_label(len(eligible), reliability_score)

        trace.extend(
            [
                f"AnalyzerAgent: objective={objective}.",
                f"AnalyzerAgent: acceptance_tier={acceptance_tier} min_accuracy={min_accuracy:.2f} max_ttft={max_ttft}.",
                f"AnalyzerAgent: eligible={len(eligible)} disqualified={len(disqualified)}.",
                f"AnalyzerAgent: selected {best_id} with score {ranked[0]['score']}.",
            ]
        )
        return AnalyzerOutput(
            best_scenario_id=best_id,
            best_row=best_row,
            ranked_scenarios=ranked,
            disqualified_scenarios=disqualified,
            reliability_score=reliability_score,
            confidence=confidence,
            gate_pass_count=gate_pass_count,
            gate_fail_count=gate_fail_count,
            overall_acceptance_status="passed" if gate_fail_count == 0 else "failed",
            trace=trace,
        )

