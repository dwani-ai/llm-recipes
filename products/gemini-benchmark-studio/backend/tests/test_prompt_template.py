from app.services.prompt_template import render_prompt_template


def test_render_prompt_template_success() -> None:
    template = "Analyze {{dataset_name}} for {{goal}}."
    rendered, missing = render_prompt_template(
        template,
        {"dataset_name": "sales_q1", "goal": "latency bottlenecks"},
    )
    assert rendered == "Analyze sales_q1 for latency bottlenecks."
    assert missing == []


def test_render_prompt_template_missing_keys() -> None:
    template = "Analyze {{dataset_name}} for {{goal}}."
    rendered, missing = render_prompt_template(template, {"dataset_name": "sales_q1"})
    assert "sales_q1" in rendered
    assert "goal" in missing

