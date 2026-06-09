from pathlib import Path

import pytest
import yaml

from p2p_engine.core.interaction_style import normalize_scale_value, scale_view
from p2p_engine.services.project_interaction_style import ProjectInteractionStyleService


def _service(root: Path) -> ProjectInteractionStyleService:
    return ProjectInteractionStyleService(root=root, p2p_dir=root / ".p2p")


def test_interaction_style_defaults_do_not_write_state(tmp_path: Path) -> None:
    service = _service(tmp_path)

    view = service.show()

    assert view.configured is False
    assert view.source == "defaults"
    assert view.technical_verbosity.value == 2
    assert view.formality.value == 2
    assert view.assertiveness.value == 0
    assert view.path == Path(".p2p/project/interaction-style.yml")
    assert not (tmp_path / ".p2p" / "project" / "interaction-style.yml").exists()


def test_interaction_style_set_persists_full_and_partial_updates(tmp_path: Path) -> None:
    service = _service(tmp_path)

    first = service.set_style(technical_verbosity=4, formality=1, assertiveness=3, actor="codex")
    second = service.set_style(formality=5, actor="owner")
    payload = yaml.safe_load((tmp_path / ".p2p" / "project" / "interaction-style.yml").read_text(encoding="utf-8"))

    assert first.configured is True
    assert first.technical_verbosity.value == 4
    assert second.technical_verbosity.value == 4
    assert second.formality.value == 5
    assert second.assertiveness.value == 3
    assert payload["interaction_style"]["updated_by"] == "owner"


def test_interaction_style_set_requires_a_change(tmp_path: Path) -> None:
    service = _service(tmp_path)

    with pytest.raises(ValueError, match="At least one interaction style value"):
        service.set_style()

    assert not (tmp_path / ".p2p" / "project" / "interaction-style.yml").exists()


@pytest.mark.parametrize("value", [-1, 6, True, False, None, 1.2, "bad", ""])
def test_interaction_style_rejects_invalid_scale_values(value: object) -> None:
    with pytest.raises(ValueError, match="Invalid interaction style value"):
        normalize_scale_value("formality", value)


def test_interaction_style_accepts_integer_literal_strings() -> None:
    assert normalize_scale_value("assertiveness", "5") == 5
    assert scale_view("technical_verbosity", "2").label == "balanced"


def test_interaction_style_validation_findings_report_malformed_present_state(tmp_path: Path) -> None:
    service = _service(tmp_path)
    path = tmp_path / ".p2p" / "project" / "interaction-style.yml"
    path.parent.mkdir(parents=True)
    path.write_text(
        yaml.safe_dump(
            {
                "interaction_style": {
                    "schema_version": 1,
                    "scope": "project",
                    "technical_verbosity": 2,
                    "formality": 9,
                    "assertiveness": 0,
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    findings = service.validation_findings()

    assert len(findings) == 1
    code, severity, finding_path, message, command = findings[0]
    assert code == "P2P250_INVALID_PROJECT_INTERACTION_STYLE"
    assert severity == "error"
    assert finding_path == path
    assert "formality" in message
    assert "p2p project interaction-style set" in command
