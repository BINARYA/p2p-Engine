from __future__ import annotations

import re

import yaml


def _yaml_dump(data: object) -> str:
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=False)


def read_title(text: str) -> str | None:
    for line in text.splitlines():
        if line.startswith("# "):
            return line.removeprefix("# ").strip()
    return None


def read_markdown_section(text: str, section: str) -> str | None:
    pattern = rf"## {re.escape(section)}\n\n(.*?)(?=\n## |\Z)"
    match = re.search(pattern, text, flags=re.DOTALL)
    if not match:
        return None
    value = match.group(1).strip()
    if not value or value in {"Pending.", "- Pending."}:
        return None
    return value


def markdown_has_section(text: str, section: str) -> bool:
    return re.search(rf"^## {re.escape(section)}\s*$", text, flags=re.MULTILINE) is not None


def read_frontmatter(text: str) -> dict[str, object]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}
    try:
        data = yaml.safe_load(text[4:end])
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}


def replace_frontmatter(text: str, frontmatter: dict[str, object]) -> str:
    body = text
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            body = text[end + len("\n---\n") :]
    return f"---\n{_yaml_dump(frontmatter)}---\n{body}"


def strip_markdown_title(content: str) -> str:
    lines = content.splitlines()
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
        if lines and not lines[0].strip():
            lines = lines[1:]
    return "\n".join(lines).strip()


def replace_section(text: str, section: str, replacement: str) -> str:
    pattern = rf"(## {re.escape(section)}\n\n)(.*?)(?=\n## |\Z)"
    return re.sub(pattern, lambda match: f"{match.group(1)}{replacement}\n", text, count=1, flags=re.DOTALL)
