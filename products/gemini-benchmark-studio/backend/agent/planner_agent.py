from dataclasses import dataclass
from typing import List

from app.schemas import BenchmarkRequest
from app.services.benchmark_runner import BenchmarkRunner, Scenario


@dataclass
class PlannerOutput:
    scenarios: List[Scenario]
    trace: List[str]


class PlannerAgent:
    def __init__(self, runner: BenchmarkRunner) -> None:
        self.runner = runner

    def plan(self, request: BenchmarkRequest) -> PlannerOutput:
        scenarios = self.runner.build_scenarios(request)
        trace = [
            "PlannerAgent: validated request constraints.",
            f"PlannerAgent: generated {len(scenarios)} scenarios.",
        ]
        return PlannerOutput(scenarios=scenarios, trace=trace)

