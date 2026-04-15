import re
from typing import Dict, List, Tuple


TEMPLATE_PATTERN = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")


def render_prompt_template(template: str, variables: Dict[str, str]) -> Tuple[str, List[str]]:
    missing: List[str] = []

    def _replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in variables or variables[key] == "":
            if key not in missing:
                missing.append(key)
            return ""
        return str(variables[key])

    rendered = TEMPLATE_PATTERN.sub(_replace, template).strip()
    rendered = re.sub(r"\s+", " ", rendered).strip()
    return rendered, missing

