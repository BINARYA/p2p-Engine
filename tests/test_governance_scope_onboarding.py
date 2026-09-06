from __future__ import annotations

from pathlib import Path

import yaml

from p2p_engine.services.agent_templates import (
    agent_policy,
    project_integration_guide,
)
from p2p_engine.storage.filesystem import P2PWorkspace

ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _prose(value: str) -> str:
    """Normalize Markdown wrapping without weakening wording assertions."""
    return " ".join(value.split())


def test_readme_leads_with_governance_scope_and_copy_ready_boundaries() -> None:
    readme = _read("README.md")

    choose = readme.index("## Choose how P2P participates")
    setup = readme.index("## 5-Minute Agent Setup")
    details = readme.index("## Detailed capabilities")
    assert choose < setup < details
    assert "`primary project-definition`" in readme
    assert "`bounded decision-memory`" in readme
    assert "## P2P Engine project-definition boundary" in readme
    assert "## P2P Engine boundary" in readme
    assert "These root instructions decide **when** P2P is used" in readme
    assert "generated `p2p-project` skill" in readme
    assert "Do not start a P2P workflow merely because" in readme
    assert "before running `p2p init`" in readme
    primary = readme[readme.index("### Dedicated project-definition repository") :]
    primary = primary[: primary.index("### Bounded service in an existing repository")]
    bounded = readme[readme.index("### Bounded service in an existing repository") :]
    bounded = bounded[: bounded.index("### Access and authority are separate")]
    assert "never edit `.p2p/` directly" in _prose(primary)
    assert "does not prove that source code was changed" in _prose(primary)
    assert "never edit `.p2p/` directly" in _prose(bounded)
    assert "does not automatically require a P2P Change Set" in _prose(bounded)


def test_readme_separates_governance_scope_from_access_and_delivery() -> None:
    readme = _read("README.md")
    prose = _prose(readme)

    assert "Governance scope answers **what P2P governs**" in prose
    assert "access profile answers **where authority and access live**" in prose
    assert "`standalone`, `linked-local`, and `remote-only`" in readme
    assert "does not automatically require a P2P Change Set" in prose
    assert "Do not duplicate one implementation plan" in prose
    assert "ADR, OpenSpec, an issue tracker, another delivery system" in prose


def test_maintained_guides_share_the_when_how_and_post_decision_model() -> None:
    agent = _read("docs/AGENT-INTEGRATION.md")
    artifacts = _read("docs/PROJECT-INTEGRATION-ARTIFACTS.md")
    concepts = _read("docs/CONCEPTS.md")
    combined = "\n".join((agent, artifacts, concepts))

    assert "primary project-definition" in combined
    assert "bounded decision-memory" in combined
    assert "WHEN P2P is used" in agent
    assert "HOW P2P is used safely" in agent
    assert "Post-Decision Routing" in agent
    assert "before `p2p init`" in artifacts
    assert "governance scope" in artifacts.lower()
    assert "access profile" in artifacts.lower()


def test_generated_policy_and_shared_skill_are_invocation_neutral(
    tmp_path: Path,
) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Scope-neutral project", agent_profile="codex")

    policy = yaml.safe_load(
        (tmp_path / ".p2p" / "agent-policy.yml").read_text(encoding="utf-8")
    )
    agents = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    skill = (
        tmp_path / ".agents" / "skills" / "p2p-project" / "SKILL.md"
    ).read_text(encoding="utf-8")

    invocation = policy["invocation_policy"]
    assert invocation == {
        "when_owner": "owner_controlled_root_instructions_or_explicit_owner_request",
        "how_owner": "generated_p2p_policy_and_skill",
        "p2p_presence_implies_invocation": False,
        "governance_scope_persisted": False,
    }
    for content in (agents, skill):
        assert "Root project instructions or an explicit owner request decide when P2P is used." in content
        assert "Generated P2P policy and skills define how routed P2P work is performed safely." in content
        assert "The presence of `.p2p/` or a P2P skill does not by itself activate a P2P workflow." in content
    assert "Use when root project instructions or the owner route work to P2P Engine." in skill
    assert "For work routed to P2P, use P2P public primitives as the source of truth" in skill
    assert "Use when working in this P2P-managed project" not in skill
    assert "source of truth for project governance and planning" not in skill


def test_every_agent_adapter_preserves_the_neutral_invocation_boundary(
    tmp_path: Path,
) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("All adapters", agent_profile="all")

    paths = (
        "AGENTS.md",
        ".agents/skills/p2p-project/SKILL.md",
        "CLAUDE.md",
        ".cursor/rules/p2p.mdc",
        ".github/copilot-instructions.md",
        "GEMINI.md",
    )
    for relative in paths:
        content = (tmp_path / relative).read_text(encoding="utf-8")
        assert "Root project instructions or an explicit owner request decide when P2P is used." in content
        assert "Use when working in this P2P-managed project" not in content
        assert "source of truth for project governance and planning" not in content


def test_bounded_init_preserves_owner_routing_outside_managed_section(
    tmp_path: Path,
) -> None:
    boundary = (
        b"# Repository instructions\r\n\r\n"
        b"P2P is bounded decision memory. Root rules decide WHEN it is used.\r\n"
    )
    (tmp_path / "AGENTS.md").write_bytes(boundary)
    workspace = P2PWorkspace(tmp_path)

    workspace.init_project("Bounded project", agent_profile="codex")
    installed = workspace.install_project_integration(
        profile="standalone",
        agent_target="codex",
    )
    after_init = (tmp_path / "AGENTS.md").read_bytes()
    assert installed.status == "applied"
    assert after_init.startswith(boundary)
    assert after_init.count(b"P2P:BEGIN managed-section") == 1

    refreshed = workspace.refresh_project_integration()
    after_refresh = (tmp_path / "AGENTS.md").read_bytes()
    assert refreshed.status == "no-change"
    assert after_refresh.startswith(boundary)
    assert after_refresh == after_init


def test_access_profile_does_not_change_invocation_policy() -> None:
    standalone = agent_policy(
        "Profile-independent scope",
        ["generic"],
        access_profile="standalone",
    )
    linked = agent_policy(
        "Profile-independent scope",
        ["generic"],
        access_profile="linked-local",
    )
    assert standalone["project_integration"]["access_profile"] == "standalone"
    assert linked["project_integration"]["access_profile"] == "linked-local"
    assert standalone["invocation_policy"] == linked["invocation_policy"]
    assert standalone["invocation_policy"]["governance_scope_persisted"] is False
    assert standalone["invocation_policy"]["p2p_presence_implies_invocation"] is False
    for profile in ("standalone", "linked-local"):
        guide = project_integration_guide(profile)
        assert f"Profile: `{profile}`" in guide
        assert "Governance scope is owner-controlled and independent" in guide
        assert "`primary project-definition`" in guide
        assert "`bounded decision-memory`" in guide
