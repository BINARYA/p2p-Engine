from __future__ import annotations


def render_governance_context(context: dict[str, str]) -> str:
    return (
        "## Governance Context\n\n"
        "### Constitution\n\n"
        f"{_fallback(context.get('constitution'))}\n\n"
        "### Decision Rules\n\n"
        f"{_fallback(context.get('decision_rules'))}\n\n"
        "### Relevance Criteria\n\n"
        f"{_fallback(context.get('relevance_criteria'))}\n"
    )


def render_missing_info_instruction() -> str:
    return (
        "Treat `Pending.`, `- Pending.`, empty arrays, and placeholder sections as missing "
        "information. Do not repeat placeholders as facts. If important information is "
        "missing, call it out explicitly in the output.\n"
    )


def _fallback(value: str | None) -> str:
    if value and value.strip():
        return value.strip()
    return "Not provided."

