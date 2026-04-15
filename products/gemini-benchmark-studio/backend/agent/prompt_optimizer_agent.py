from dataclasses import dataclass
from typing import Dict, List

from app.schemas import PromptOptimizationRequest, PromptOptimizationResponse, PromptVariant
from app.services.prompt_template import render_prompt_template


def _ensure_locked_phrases(template: str, locked_phrases: List[str]) -> str:
    output = template
    for phrase in locked_phrases:
        phrase = phrase.strip()
        if phrase and phrase.lower() not in output.lower():
            output = f"{output}\nMandatory term: {phrase}"
    return output


def _quality_proxy_score(rendered_prompt: str) -> float:
    score = 5.0
    text = rendered_prompt.lower()
    if "bullet" in text or "steps" in text:
        score += 1.0
    if "be concise" in text or "concise" in text:
        score += 0.5
    if "verify" in text or "validate" in text:
        score += 0.5
    if len(rendered_prompt) > 400:
        score -= 0.5
    return max(1.0, min(10.0, score))


@dataclass
class PromptPlannerOutput:
    objective: str
    trace: List[str]


class PromptPlannerAgent:
    def plan(self, request: PromptOptimizationRequest) -> PromptPlannerOutput:
        allowed = {"lowest_latency", "highest_quality", "balanced"}
        objective = request.objective if request.objective in allowed else "balanced"
        trace = [
            "PromptPlannerAgent: validated optimization objective and constraints.",
            f"PromptPlannerAgent: objective={objective}, variants={request.variant_count}.",
        ]
        return PromptPlannerOutput(objective=objective, trace=trace)


class PromptRewriterAgent:
    def generate_variants(self, request: PromptOptimizationRequest) -> List[Dict[str, str]]:
        template = request.template.strip()
        variants: List[Dict[str, str]] = [
            {
                "variant_id": "latency_compact",
                "template": _ensure_locked_phrases(
                    f"{template}\nKeep answer short. Use 4 bullet points max. Be concise.",
                    request.locked_phrases,
                ),
                "reasoning": "Compact rewrite reduces completion overhead for lower latency.",
            },
            {
                "variant_id": "quality_structured",
                "template": _ensure_locked_phrases(
                    f"{template}\nProvide: assumptions, analysis, recommendations, risks.",
                    request.locked_phrases,
                ),
                "reasoning": "Structured sections improve consistency and answer completeness.",
            },
            {
                "variant_id": "cache_friendly",
                "template": _ensure_locked_phrases(
                    f"System context:\n{{{{data_context}}}}\n\nTask:\n{template}\n"
                    "Reuse context and avoid repeating unchanged details.",
                    request.locked_phrases,
                ),
                "reasoning": "Stable shared prefix is better for context reuse and cache behavior.",
            },
        ]

        # Add light variants if user asks for more than 3.
        while len(variants) < request.variant_count:
            idx = len(variants) + 1
            variants.append(
                {
                    "variant_id": f"custom_variant_{idx}",
                    "template": _ensure_locked_phrases(
                        f"{template}\nFocus on practical benchmarking decisions only.",
                        request.locked_phrases,
                    ),
                    "reasoning": "Additional practical-focused variant for broader search.",
                }
            )
        return variants[: request.variant_count]


class PromptEvaluatorAgent:
    def rank(
        self,
        objective: str,
        variants: List[PromptVariant],
    ) -> List[PromptVariant]:
        if objective == "lowest_latency":
            key_fn = lambda item: (-item.quality_proxy_score, len(item.rendered_prompt))
        elif objective == "highest_quality":
            key_fn = lambda item: (len(item.rendered_prompt), -item.quality_proxy_score)
        else:
            key_fn = lambda item: (-item.quality_proxy_score, len(item.rendered_prompt))
        return sorted(variants, key=key_fn)


class PromptOptimizerAgent:
    def __init__(self) -> None:
        self.planner = PromptPlannerAgent()
        self.rewriter = PromptRewriterAgent()
        self.evaluator = PromptEvaluatorAgent()

    def optimize(self, request: PromptOptimizationRequest) -> PromptOptimizationResponse:
        planner = self.planner.plan(request)
        trace = list(planner.trace)

        raw_variants = self.rewriter.generate_variants(request)
        variants: List[PromptVariant] = []
        for raw in raw_variants:
            rendered, _ = render_prompt_template(raw["template"], request.variables)
            score = _quality_proxy_score(rendered)
            variants.append(
                PromptVariant(
                    variant_id=raw["variant_id"],
                    template=raw["template"],
                    rendered_prompt=rendered,
                    quality_proxy_score=score,
                    reasoning=raw["reasoning"],
                )
            )
        trace.append(f"PromptRewriterAgent: generated {len(variants)} variants.")

        ranked = self.evaluator.rank(planner.objective, variants)
        winner = ranked[0]
        trace.append(
            f"PromptEvaluatorAgent: selected {winner.variant_id} with score {winner.quality_proxy_score:.2f}."
        )

        return PromptOptimizationResponse(
            objective=planner.objective,
            winner_variant_id=winner.variant_id,
            winner_template=winner.template,
            variants=ranked,
            trace=trace,
        )

