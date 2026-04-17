from agent.analyzer_agent import AnalyzerAgent


def _summary(
    scenario_id: str,
    ttft: float | None,
    ttft_p95: float | None,
    e2e: float | None,
    ok: int,
    unsupported: int,
    error: int,
    samples: int,
) -> dict:
    return {
        "scenario_id": scenario_id,
        "ttft_p50_s": ttft,
        "ttft_p95_s": ttft_p95,
        "e2e_p50_s": e2e,
        "tokens_per_s_avg": 20.0,
        "ok_count": ok,
        "unsupported_count": unsupported,
        "error_count": error,
        "samples": samples,
    }


def test_analyzer_ranks_eligible_and_disqualifies_unstable() -> None:
    analyzer = AnalyzerAgent()
    summaries = [
        _summary("scenario_fast", 0.28, 0.45, 1.2, ok=8, unsupported=0, error=0, samples=10),
        _summary("scenario_balanced", 0.31, 0.48, 1.1, ok=9, unsupported=0, error=0, samples=10),
        _summary("scenario_unstable", 0.20, 0.80, 1.5, ok=2, unsupported=3, error=5, samples=10),
    ]
    output = analyzer.analyze(summaries, objective="balanced")

    assert output.best_scenario_id in {"scenario_fast", "scenario_balanced"}
    assert len(output.ranked_scenarios) == 2
    assert output.disqualified_scenarios[0]["scenario_id"] == "scenario_unstable"
    assert output.reliability_score > 0.6
    assert output.confidence in {"medium", "high"}


def test_analyzer_returns_low_confidence_when_no_eligible_rows() -> None:
    analyzer = AnalyzerAgent()
    summaries = [
        _summary("scenario_failed", None, None, None, ok=0, unsupported=4, error=6, samples=10),
    ]
    output = analyzer.analyze(summaries, objective="lowest_latency")

    assert output.best_scenario_id is None
    assert output.ranked_scenarios == []
    assert output.confidence == "low"
    assert output.disqualified_scenarios[0]["reason"] == "no_successful_trials"
