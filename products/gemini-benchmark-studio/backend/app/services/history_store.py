import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def utc_now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


class BenchmarkHistoryStore:
    def __init__(self, history_file: Optional[Path] = None) -> None:
        default_path = Path(__file__).resolve().parents[2] / "outputs" / "history.jsonl"
        self.history_file = history_file or default_path
        self.history_file.parent.mkdir(parents=True, exist_ok=True)

    def save_run(
        self,
        run_id: str,
        request_snapshot: Dict[str, Any],
        best_scenario_id: Optional[str],
        summaries_count: int,
        artifacts: Dict[str, str],
    ) -> None:
        row = {
            "saved_at": utc_now_iso(),
            "run_id": run_id,
            "best_scenario_id": best_scenario_id,
            "summaries_count": summaries_count,
            "request": request_snapshot,
            "artifacts": artifacts,
        }
        with self.history_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")

    def list_runs(self, limit: int = 25) -> List[Dict[str, Any]]:
        if not self.history_file.exists():
            return []
        rows: List[Dict[str, Any]] = []
        with self.history_file.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        rows.reverse()
        return rows[:limit]

