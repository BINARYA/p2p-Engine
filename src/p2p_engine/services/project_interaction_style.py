from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml

from p2p_engine.foundation.yaml_loaders import load_yaml

from p2p_engine.core.interaction_style import (
    ASSERTIVENESS,
    FORMALITY,
    INTERACTION_STYLE_SCHEMA_VERSION,
    INTERACTION_STYLE_SCOPE,
    InteractionStyle,
    InteractionStyleUpdate,
    InteractionStyleView,
    TECHNICAL_VERBOSITY,
    default_interaction_style,
    interaction_style_from_payload,
    normalize_scale_value,
    scale_view,
    validate_interaction_style_payload,
)
from p2p_engine.foundation.files import relative_to_root as _relative_to_root
from p2p_engine.foundation.files import yaml_dump as _yaml_dump

INTERACTION_STYLE_FILENAME = "interaction-style.yml"
INTERACTION_STYLE_RECOVERY_COMMAND = (
    "p2p project interaction-style set "
    "--technical-verbosity 2 --formality 2 --assertiveness 0"
)


@dataclass(frozen=True)
class InteractionStyleValidationIssue:
    field: str
    message: str
    severity: str = "error"


class ProjectInteractionStyleService:
    def __init__(self, *, root: Path, p2p_dir: Path) -> None:
        self.root = root
        self.p2p_dir = p2p_dir

    def path(self) -> Path:
        return self.p2p_dir / "project" / INTERACTION_STYLE_FILENAME

    def show(self) -> InteractionStyleView:
        path = self.path()
        if not path.exists():
            return self._view(default_interaction_style(), configured=False, source="defaults")
        payload = _read_yaml_mapping(path)
        validate_interaction_style_payload(payload)
        state = payload["interaction_style"]
        if not isinstance(state, dict):
            raise ValueError("Interaction style must define top-level `interaction_style` mapping.")
        return self._view(
            interaction_style_from_payload(state),
            configured=True,
            source="configured",
            updated_at=str(state.get("updated_at") or ""),
            updated_by=str(state.get("updated_by") or ""),
        )

    def set_style(
        self,
        *,
        technical_verbosity: int | str | None = None,
        formality: int | str | None = None,
        assertiveness: int | str | None = None,
        actor: str = "local",
    ) -> InteractionStyleView:
        update = InteractionStyleUpdate(
            technical_verbosity=(
                normalize_scale_value(TECHNICAL_VERBOSITY, technical_verbosity)
                if technical_verbosity is not None
                else None
            ),
            formality=normalize_scale_value(FORMALITY, formality) if formality is not None else None,
            assertiveness=normalize_scale_value(ASSERTIVENESS, assertiveness) if assertiveness is not None else None,
        )
        if not update.has_changes():
            raise ValueError("At least one interaction style value is required.")

        current = self.show()
        style = InteractionStyle(
            technical_verbosity=(
                update.technical_verbosity
                if update.technical_verbosity is not None
                else current.technical_verbosity.value
            ),
            formality=update.formality if update.formality is not None else current.formality.value,
            assertiveness=update.assertiveness if update.assertiveness is not None else current.assertiveness.value,
        )
        payload = self._payload(style, actor=actor)
        validate_interaction_style_payload(payload)
        _atomic_write(self.path(), _yaml_dump(payload))
        return self.show()

    def validation_findings(self) -> list[tuple[str, str, Path, str, str]]:
        path = self.path()
        if not path.exists():
            return []
        try:
            validate_interaction_style_payload(_read_yaml_mapping(path))
        except (ValueError, yaml.YAMLError) as exc:
            return [
                (
                    "P2P250_INVALID_PROJECT_INTERACTION_STYLE",
                    "error",
                    path,
                    str(exc),
                    INTERACTION_STYLE_RECOVERY_COMMAND,
                )
            ]
        return []

    def _view(
        self,
        style: InteractionStyle,
        *,
        configured: bool,
        source: str,
        updated_at: str = "",
        updated_by: str = "",
    ) -> InteractionStyleView:
        return InteractionStyleView(
            schema_version=INTERACTION_STYLE_SCHEMA_VERSION,
            scope=INTERACTION_STYLE_SCOPE,
            configured=configured,
            source=source,
            path=_relative_to_root(self.path(), self.root),
            technical_verbosity=scale_view(TECHNICAL_VERBOSITY, style.technical_verbosity),
            formality=scale_view(FORMALITY, style.formality),
            assertiveness=scale_view(ASSERTIVENESS, style.assertiveness),
            updated_at=updated_at,
            updated_by=updated_by,
        )

    def _payload(self, style: InteractionStyle, *, actor: str) -> dict[str, object]:
        return {
            "interaction_style": {
                "schema_version": INTERACTION_STYLE_SCHEMA_VERSION,
                "scope": INTERACTION_STYLE_SCOPE,
                "technical_verbosity": style.technical_verbosity,
                "formality": style.formality,
                "assertiveness": style.assertiveness,
                "updated_at": _now(),
                "updated_by": str(actor or "local").strip() or "local",
            }
        }


def _read_yaml_mapping(path: Path) -> dict[str, object]:
    data = load_yaml(path.read_bytes())
    if not isinstance(data, dict):
        raise ValueError(f"Invalid interaction style YAML mapping: {path}")
    return data


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.tmp")
    temp_path.write_text(content, encoding="utf-8")
    temp_path.replace(path)
