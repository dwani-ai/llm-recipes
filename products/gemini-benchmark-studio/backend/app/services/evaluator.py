import json
import re
from dataclasses import dataclass
from typing import Any, Dict, Optional

from app.schemas import BenchmarkRequest, EvaluationConfig


@dataclass
class EvaluationResult:
    status: str
    accuracy_score: Optional[float]
    criteria_scores: Dict[str, float]
    rationale: Optional[str]
    error: Optional[str]


def _clamp_01(value: Any) -> Optional[float]:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return max(0.0, min(1.0, numeric))


def _extract_json_payload(text: str) -> Dict[str, Any]:
    if not text.strip():
        raise ValueError("empty_judge_output")
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        raise ValueError("judge_output_not_json")
    parsed = json.loads(match.group(0))
    if not isinstance(parsed, dict):
        raise ValueError("judge_json_not_object")
    return parsed


def build_rubric_prompt(
    eval_config: EvaluationConfig,
    rendered_prompt: str,
    data_context: str,
    model_output: str,
    acceptance_tier: str,
) -> str:
    criteria_lines = []
    for criterion in eval_config.rubric_criteria:
        criteria_lines.append(
            f"- {criterion.key}: {criterion.label} (weight={criterion.weight:.2f}) -> {criterion.description}"
        )
    return (
        "You are an evaluation judge for LLM benchmark acceptance testing.\n"
        "Score the candidate output using the rubric and return strict JSON only.\n\n"
        f"Acceptance tier: {acceptance_tier}\n"
        "Rubric criteria:\n"
        f"{chr(10).join(criteria_lines)}\n\n"
        "Required JSON schema:\n"
        "{\n"
        '  "overall_score": 0.0_to_1.0,\n'
        '  "criteria_scores": {"criterion_key": 0.0_to_1.0},\n'
        '  "rationale": "short explanation"\n'
        "}\n\n"
        "Prompt shown to candidate model:\n"
        f"{rendered_prompt}\n\n"
        "Provided dataset context:\n"
        f"{data_context}\n\n"
        "Candidate model output:\n"
        f"{model_output}\n"
    )


class RubricEvaluator:
    def __init__(self, request: BenchmarkRequest) -> None:
        self.request = request
        self.eval_config = request.evaluation

    def evaluate(
        self,
        rendered_prompt: str,
        data_context: str,
        model_output: str,
        acceptance_tier: str,
    ) -> EvaluationResult:
        prompt = build_rubric_prompt(
            eval_config=self.eval_config,
            rendered_prompt=rendered_prompt,
            data_context=data_context,
            model_output=model_output,
            acceptance_tier=acceptance_tier,
        )
        try:
            judge_text = self._invoke_judge(prompt=prompt)
            parsed = _extract_json_payload(judge_text)
            criteria_scores_raw = parsed.get("criteria_scores", {})
            criteria_scores: Dict[str, float] = {}
            if isinstance(criteria_scores_raw, dict):
                for key, value in criteria_scores_raw.items():
                    maybe_score = _clamp_01(value)
                    if maybe_score is not None:
                        criteria_scores[str(key)] = maybe_score
            overall = _clamp_01(parsed.get("overall_score"))
            if overall is None and criteria_scores:
                weighted_total = 0.0
                weight_sum = 0.0
                for criterion in self.eval_config.rubric_criteria:
                    score = criteria_scores.get(criterion.key)
                    if score is None:
                        continue
                    weighted_total += score * criterion.weight
                    weight_sum += criterion.weight
                if weight_sum > 0:
                    overall = weighted_total / weight_sum
            if overall is None:
                raise ValueError("judge_missing_overall_score")
            rationale = parsed.get("rationale")
            if not isinstance(rationale, str):
                rationale = "Judge did not provide rationale."
            return EvaluationResult(
                status="ok",
                accuracy_score=overall,
                criteria_scores=criteria_scores,
                rationale=rationale,
                error=None,
            )
        except Exception as exc:
            return EvaluationResult(
                status="evaluation_error",
                accuracy_score=None,
                criteria_scores={},
                rationale=None,
                error=f"{type(exc).__name__}: {exc}",
            )

    def _invoke_judge(self, prompt: str) -> str:
        stack = self.eval_config.judge_stack
        if stack == "google_genai":
            return self._invoke_google_genai(prompt)
        if stack == "openai_compat":
            return self._invoke_openai_compat(prompt)
        return self._invoke_vertex_api(prompt)

    def _invoke_google_genai(self, prompt: str) -> str:
        if not self.request.api_key:
            raise RuntimeError("api_key is required for google_genai evaluation.")
        try:
            from google import genai
        except ImportError as exc:
            raise RuntimeError("google-genai is not installed.") from exc
        client = genai.Client(api_key=self.request.api_key)
        response = client.models.generate_content(
            model=self.eval_config.judge_model,
            contents=[{"role": "user", "parts": [{"text": prompt}]}],
            config={"temperature": 0.0, "max_output_tokens": 512},
        )
        text = getattr(response, "text", "") or ""
        if not text.strip():
            raise RuntimeError("empty_judge_response")
        return text

    def _invoke_openai_compat(self, prompt: str) -> str:
        if not self.request.api_key:
            raise RuntimeError("api_key is required for openai_compat evaluation.")
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("openai package is not installed.") from exc
        client = OpenAI(
            api_key=self.request.api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )
        response = client.chat.completions.create(
            model=self.eval_config.judge_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=512,
            stream=False,
        )
        text = response.choices[0].message.content or ""
        if not text.strip():
            raise RuntimeError("empty_judge_response")
        return text

    def _invoke_vertex_api(self, prompt: str) -> str:
        if self.request.vertex_config is None:
            raise RuntimeError("vertex_config is required for vertex_api evaluation.")
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("openai package is not installed.") from exc
        token = self.request.vertex_config.access_token
        if not token:
            try:
                from google.auth import default
                from google.auth.transport.requests import Request
            except ImportError as exc:
                raise RuntimeError(
                    "google-auth is required for Vertex ADC token fallback."
                ) from exc
            credentials, _ = default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
            credentials.refresh(Request())
            token = getattr(credentials, "token", None)
            if not token:
                raise RuntimeError("Unable to obtain ADC access token for Vertex evaluation.")
        base_url = (
            f"https://{self.request.vertex_config.location}-aiplatform.googleapis.com/v1/"
            f"projects/{self.request.vertex_config.project_id}/locations/{self.request.vertex_config.location}/"
            f"endpoints/{self.request.vertex_config.endpoint_id}"
        )
        client = OpenAI(api_key=token, base_url=base_url)
        response = client.chat.completions.create(
            model=self.eval_config.judge_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=512,
            stream=False,
        )
        text = response.choices[0].message.content or ""
        if not text.strip():
            raise RuntimeError("empty_judge_response")
        return text
