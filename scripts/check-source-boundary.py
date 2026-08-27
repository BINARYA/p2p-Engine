#!/usr/bin/env python3
from __future__ import annotations

import ast
import re
import sys
from importlib.util import find_spec
from pathlib import Path

REMOVED_RUNTIME_FILES = {
    "src/p2p_engine/storage/git.py",
    "src/p2p_engine/services/sync.py",
    "src/p2p_engine/services/proposal_branches.py",
    "src/p2p_engine/services/work_branches.py",
    "src/p2p_engine/services/proposal_drafts.py",
    "src/p2p_engine/services/gitignore_hygiene.py",
    "src/p2p_engine/services/remote_profile.py",
    "src/p2p_engine/cli_commands/proposal_branches.py",
    "src/p2p_engine/mcp/handlers/collaboration_remote.py",
    "src/p2p_engine/mcp/handlers/collaboration_sync.py",
    "src/p2p_engine/mcp/handlers/collaboration_proposals.py",
}
REMOVED_ORPHANS = {
    "src/p2p_engine/core/project.py": "p2p_engine.core.project",
    "src/p2p_engine/core/task.py": "p2p_engine.core.task",
    "src/p2p_engine/core/plan.py": "p2p_engine.core.plan",
    "src/p2p_engine/exporters/markdown.py": "p2p_engine.exporters.markdown",
    "src/p2p_engine/exporters/openspec.py": "p2p_engine.exporters.openspec",
}
REMOVED_MCP_TOOLS = {
    "p2p_sync_status", "p2p_sync_fetch", "p2p_sync_pull", "p2p_sync_push",
    "p2p_project_remote_show", "p2p_project_remote_configure",
    "p2p_proposal_draft_commit", "p2p_proposal_branch",
    "p2p_proposal_branch_status", "p2p_proposal_publish",
    "p2p_proposal_request_review", "p2p_proposal_accept_branch",
    "p2p_proposal_reject_branch", "p2p_proposal_merge",
    "p2p_proposal_finalize", "p2p_proposal_cleanup",
    "p2p_proposal_branch_scan", "p2p_work_branch", "p2p_work_submit",
    "p2p_work_review", "p2p_work_publish", "p2p_work_request_review",
    "p2p_work_accept", "p2p_work_finalize", "p2p_work_cleanup",
}
REMOVED_CONSENT_OPERATIONS = {
    "sync_fetch", "sync_pull", "sync_push", "proposal_publish",
    "proposal_request_review", "proposal_accept_branch", "proposal_reject_branch",
    "proposal_merge", "proposal_finalize", "proposal_cleanup", "work_publish",
    "work_request_review", "work_accept", "work_finalize", "work_cleanup",
}
REMOVED_CLI_PATHS = {
    "sync", "project remote", "change policy", "proposal branch",
    "proposal publish", "proposal request-review", "proposal accept-branch",
    "proposal reject-branch", "proposal merge", "proposal finalize",
    "proposal cleanup", "proposal retire-branch", "proposal scan",
    "work scan", "work branch", "work submit", "work review", "work publish",
    "work request-review", "work accept", "work finalize", "work cleanup",
}


def _literal_git_invocations(path: Path) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    hits: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        function = node.func
        if not (
            isinstance(function, ast.Attribute)
            and isinstance(function.value, ast.Name)
            and function.value.id == "subprocess"
        ):
            continue
        command = node.args[0]
        if not isinstance(command, (ast.List, ast.Tuple)) or not command.elts:
            continue
        first = command.elts[0]
        if isinstance(first, ast.Constant) and first.value == "git":
            hits.append(node.lineno)
    return hits


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    issues: list[str] = []
    for relative in sorted(REMOVED_RUNTIME_FILES | set(REMOVED_ORPHANS)):
        if (root / relative).exists():
            issues.append(f"removed package member exists: {relative}")
    for relative, module in REMOVED_ORPHANS.items():
        if find_spec(module) is not None:
            issues.append(f"removed module remains importable: {module} ({relative})")

    for path in sorted((root / "src" / "p2p_engine").rglob("*.py")):
        for line in _literal_git_invocations(path):
            issues.append(f"runtime git subprocess invocation: {path.relative_to(root)}:{line}")

    sys.path.insert(0, str(root / "src"))
    from typer.testing import CliRunner

    from p2p_engine.cli import app
    from p2p_engine.mcp.registry import TOOL_NAMES
    from p2p_engine.services.agent_templates import agent_instruction_files
    from p2p_engine.services.consent import CONSENT_OPERATIONS

    names = set(TOOL_NAMES)
    for name in sorted(REMOVED_MCP_TOOLS & names):
        issues.append(f"removed MCP tool remains registered: {name}")
    for operation in sorted(REMOVED_CONSENT_OPERATIONS & CONSENT_OPERATIONS):
        issues.append(f"removed consent operation remains registered: {operation}")

    runner = CliRunner()
    help_commands = {
        "": ["--help"],
        "project": ["project", "--help"],
        "change": ["change", "--help"],
        "proposal": ["proposal", "--help"],
        "work": ["work", "--help"],
    }
    help_text = {
        group: runner.invoke(app, args, color=False).output.lower()
        for group, args in help_commands.items()
    }
    for command in sorted(REMOVED_CLI_PATHS):
        group, _, leaf = command.partition(" ")
        target = help_text.get(group, help_text[""])
        token = leaf or group
        if re.search(rf"(?m)^\s*{re.escape(token)}\s+", target):
            issues.append(f"removed CLI command remains in help: p2p {command}")

    rendered = "\n".join(
        agent_instruction_files(
            "Boundary Test",
            ["generic", "codex", "claude", "cursor", "copilot", "gemini", "opencode"],
        ).values()
    )
    for token in sorted(REMOVED_MCP_TOOLS | REMOVED_CONSENT_OPERATIONS):
        if token in rendered:
            issues.append(f"removed source-control guidance remains generated: {token}")
    for token in ("p2p sync ", "p2p proposal branch", "p2p work branch", "raw git"):
        if token in rendered.lower():
            issues.append(f"removed source-control guidance remains generated: {token}")

    if issues:
        for issue in issues:
            print(f"source boundary: {issue}")
        return 1
    print(
        "source boundary verified: "
        f"removed_runtime={len(REMOVED_RUNTIME_FILES)} "
        f"removed_orphans={len(REMOVED_ORPHANS)} removed_mcp={len(REMOVED_MCP_TOOLS)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

