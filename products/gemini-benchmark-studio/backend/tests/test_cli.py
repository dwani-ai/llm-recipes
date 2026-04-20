import json

import pytest

from app.cli import build_mode_selection, load_variables_json, merge_variables, parse_kv_var


def test_parse_kv_var_ok() -> None:
    key, value = parse_kv_var("dataset_name=tickets")
    assert key == "dataset_name"
    assert value == "tickets"


def test_parse_kv_var_invalid() -> None:
    with pytest.raises(ValueError):
        parse_kv_var("badpair")


def test_load_variables_json(tmp_path) -> None:
    path = tmp_path / "vars.json"
    path.write_text(json.dumps({"dataset_name": "tickets", "goal": "latency"}), encoding="utf-8")
    vars_data = load_variables_json(str(path))
    assert vars_data["dataset_name"] == "tickets"
    assert vars_data["goal"] == "latency"


def test_merge_variables_cli_overrides_file() -> None:
    merged = merge_variables({"goal": "quality", "dataset_name": "kb"}, ["goal=latency"])
    assert merged["goal"] == "latency"
    assert merged["dataset_name"] == "kb"


def test_build_mode_selection_non_streaming_thinking_default_shape() -> None:
    mode = build_mode_selection(streaming=False, thinking=True, cache_intent="none")
    assert mode.streaming is False
    assert mode.thinking is True
    assert mode.implicit_cache is False
    assert mode.explicit_cache is False
