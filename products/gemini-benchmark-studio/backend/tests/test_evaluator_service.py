from app.schemas import BenchmarkRequest
from app.services.evaluator import RubricEvaluator


def _request() -> BenchmarkRequest:
    return BenchmarkRequest(
        api_key="dummy_api_key_123456789",
        stacks=["google_genai"],
        models=["gemini-2.5-flash"],
        trials=1,
        warmup_trials=0,
        prompt_template="Analyze {{dataset_name}} for {{goal}}",
        prompt_variables={"dataset_name": "tickets", "goal": "latency", "data_context": "sample context"},
        evaluation_enabled=True,
    )


def test_evaluator_parses_strict_json(monkeypatch) -> None:
    evaluator = RubricEvaluator(_request())

    def fake_invoke(prompt: str) -> str:
        assert prompt
        return (
            '{"overall_score": 0.82, "criteria_scores": {"factuality": 0.8, "completeness": 0.9}, '
            '"rationale": "Good coverage and grounded output."}'
        )

    monkeypatch.setattr(evaluator, "_invoke_judge", fake_invoke)
    result = evaluator.evaluate(
        rendered_prompt="Analyze dataset.",
        data_context="context",
        model_output="model output",
        acceptance_tier="standard",
    )

    assert result.status == "ok"
    assert result.accuracy_score == 0.82
    assert result.criteria_scores["factuality"] == 0.8
    assert "grounded" in (result.rationale or "")


def test_evaluator_returns_evaluation_error_for_non_json(monkeypatch) -> None:
    evaluator = RubricEvaluator(_request())

    def fake_invoke(prompt: str) -> str:
        assert prompt
        return "Judge crashed and returned plain text."

    monkeypatch.setattr(evaluator, "_invoke_judge", fake_invoke)
    result = evaluator.evaluate(
        rendered_prompt="Analyze dataset.",
        data_context="context",
        model_output="model output",
        acceptance_tier="standard",
    )

    assert result.status == "evaluation_error"
    assert result.accuracy_score is None
    assert result.error is not None
