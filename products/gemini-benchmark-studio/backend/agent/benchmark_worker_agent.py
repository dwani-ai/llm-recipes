from dataclasses import dataclass
from typing import Any, Dict, List

from app.schemas import BenchmarkRequest
from app.services.benchmark_runner import BenchmarkRunner


@dataclass
class BenchmarkWorkerOutput:
    run_payload: Dict[str, Any]
    trace: List[str]


class BenchmarkWorkerAgent:
    def __init__(self, runner: BenchmarkRunner) -> None:
        self.runner = runner

    def run(self, request: BenchmarkRequest, rendered_prompt: str) -> BenchmarkWorkerOutput:
        payload = self.runner.run(request, rendered_prompt)
        trace = [
            f"BenchmarkWorkerAgent: completed run {payload['run_id']}.",
            f"BenchmarkWorkerAgent: produced {len(payload['summaries'])} summary rows.",
        ]
        return BenchmarkWorkerOutput(run_payload=payload, trace=trace)

