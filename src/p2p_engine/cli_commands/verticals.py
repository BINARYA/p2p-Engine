from __future__ import annotations

from pathlib import Path

import typer

from p2p_engine.cli_contract import error_envelope, print_json, success_envelope
from p2p_engine.cli_shared import console, fail
from p2p_engine.core.vertical_drafts import VERTICAL_DRAFT_MAX_DOCUMENT_BYTES
from p2p_engine.foundation.yaml_loaders import load_yaml
from p2p_engine.services.vertical_catalog import (
    VerticalCatalogService,
    VerticalPullService,
)
from p2p_engine.services.vertical_registry import (
    VerticalRegistryClient,
    VerticalRegistryConfigurationService,
)
from p2p_engine.services.vertical_draft_lifecycle import VerticalDraftLifecycleService
from p2p_engine.services.vertical_drafts import VerticalDraftService


def register_vertical_commands(vertical_app: typer.Typer) -> None:
    registry_app = typer.Typer(help="Configure remote vertical registries")
    draft_app = typer.Typer(help="Author mutable vertical drafts and immutable releases")
    vertical_app.add_typer(registry_app, name="registry")
    vertical_app.add_typer(draft_app, name="draft")

    @draft_app.command("create")
    def draft_create(
        empty: bool = typer.Option(False, "--empty", help="Start with no governed sections"),
        source_coordinate: str = typer.Option(
            "",
            "--from",
            help="Clone one exact local release",
        ),
        publisher: str = typer.Option("", "--publisher"),
        vertical_id: str = typer.Option("", "--vertical-id"),
        version: str = typer.Option("", "--version"),
        license_id: str = typer.Option("", "--license"),
        name: str = typer.Option("", "--name"),
        description: str = typer.Option("", "--description"),
        visibility: str = typer.Option("private", "--visibility"),
        extends: str = typer.Option("", "--extends"),
        forked_from: str = typer.Option("", "--forked-from"),
        previous_release: str = typer.Option("", "--previous-release"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root for local pack lookup"),
        output_format: str = typer.Option("json", "--format", help="Output format: text or json"),
    ) -> None:
        """Create an empty draft or clone one exact local release."""
        try:
            if empty == bool(source_coordinate):
                raise ValueError(
                    "P2P_VERTICAL_DRAFT_CREATE_MODE_REQUIRED: choose exactly one of --empty or --from"
                )
            service = VerticalDraftService(root)
            if empty:
                result = service.create_empty(
                    publisher=publisher,
                    vertical_id=vertical_id,
                    version=version,
                    license_id=license_id,
                    name=name,
                    description=description,
                    visibility=visibility,
                )
            else:
                result = service.create_from(
                    source_coordinate,
                    publisher=publisher,
                    vertical_id=vertical_id,
                    version=version,
                    license_id=license_id,
                    name=name,
                    description=description,
                    visibility=visibility,
                    extends=extends,
                    forked_from=forked_from,
                    previous_release=previous_release,
                )
        except ValueError as exc:
            _operation_error("vertical.draft.create", exc, output_format)
        _draft_output("vertical.draft.create", result, output_format)

    @draft_app.command("inspect")
    def draft_inspect(
        draft_id: str = typer.Argument(...),
        root: Path = typer.Option(Path.cwd(), "--root"),
        output_format: str = typer.Option("json", "--format", help="Output format: text or json"),
    ) -> None:
        """Read the complete normalized draft and current evidence."""
        try:
            result = VerticalDraftService(root).inspect(draft_id)
        except ValueError as exc:
            _operation_error("vertical.draft.inspect", exc, output_format)
        _draft_output("vertical.draft.inspect", result, output_format)

    @draft_app.command("update")
    def draft_update(
        draft_id: str = typer.Argument(...),
        document: Path = typer.Option(..., "--document", help="Complete normalized JSON or YAML document"),
        expected_revision: int | None = typer.Option(None, "--expected-revision"),
        expected_hash: str = typer.Option("", "--expected-hash"),
        root: Path = typer.Option(Path.cwd(), "--root"),
        output_format: str = typer.Option("json", "--format", help="Output format: text or json"),
    ) -> None:
        """Replace a complete draft under an optimistic precondition."""
        try:
            payload = _load_draft_document(document)
            result = VerticalDraftService(root).update(
                draft_id,
                payload,
                expected_revision=expected_revision,
                expected_hash=expected_hash,
            )
        except ValueError as exc:
            _operation_error("vertical.draft.update", exc, output_format)
        _draft_output("vertical.draft.update", result, output_format)

    @draft_app.command("materialize")
    def draft_materialize(
        draft_id: str = typer.Argument(...),
        target: Path = typer.Argument(..., help="Fresh canonical pack directory"),
        root: Path = typer.Option(Path.cwd(), "--root"),
        output_format: str = typer.Option("json", "--format", help="Output format: text or json"),
    ) -> None:
        """Compile the normalized document into a canonical schema-2 pack."""
        try:
            result = VerticalDraftLifecycleService(root).materialize(draft_id, target)
        except ValueError as exc:
            _operation_error("vertical.draft.materialize", exc, output_format)
        _draft_output("vertical.draft.materialize", result, output_format)

    @draft_app.command("validate")
    def draft_validate(
        draft_id: str = typer.Argument(...),
        root: Path = typer.Option(Path.cwd(), "--root"),
        output_format: str = typer.Option("json", "--format", help="Output format: text or json"),
    ) -> None:
        """Validate current draft and materialization and record bound evidence."""
        try:
            result = VerticalDraftLifecycleService(root).validate(draft_id)
        except ValueError as exc:
            _operation_error("vertical.draft.validate", exc, output_format)
        _draft_output("vertical.draft.validate", result, output_format)

    @draft_app.command("package")
    def draft_package(
        draft_id: str = typer.Argument(...),
        output: Path = typer.Argument(..., help="Portable .p2pv output"),
        root: Path = typer.Option(Path.cwd(), "--root"),
        output_format: str = typer.Option("json", "--format", help="Output format: text or json"),
    ) -> None:
        """Package the current validated materialization deterministically."""
        try:
            result = VerticalDraftLifecycleService(root).package(draft_id, output)
        except ValueError as exc:
            _operation_error("vertical.draft.package", exc, output_format)
        _draft_output("vertical.draft.package", result, output_format)

    @draft_app.command("add-local")
    def draft_add_local(
        draft_id: str = typer.Argument(...),
        root: Path = typer.Option(Path.cwd(), "--root"),
        output_format: str = typer.Option("json", "--format", help="Output format: text or json"),
    ) -> None:
        """Add the verified exact release to the immutable user cache."""
        try:
            result = VerticalDraftLifecycleService(root).add_local(draft_id)
        except ValueError as exc:
            _operation_error("vertical.draft.add-local", exc, output_format)
        _draft_output("vertical.draft.add-local", result, output_format)

    @draft_app.command("publish")
    def draft_publish(
        draft_id: str = typer.Argument(...),
        registry: str = typer.Option("", "--registry"),
        idempotency_key: str = typer.Option(..., "--idempotency-key"),
        root: Path = typer.Option(Path.cwd(), "--root"),
        output_format: str = typer.Option("json", "--format", help="Output format: text or json"),
    ) -> None:
        """Publish the exact verified artifact through an authenticated registry."""
        try:
            client = VerticalRegistryClient()
            result = VerticalDraftLifecycleService(root, client=client).publish(
                draft_id,
                registry=registry,
                idempotency_key=idempotency_key,
            )
        except ValueError as exc:
            _operation_error("vertical.draft.publish", exc, output_format)
        _draft_output("vertical.draft.publish", result, output_format)

    @vertical_app.command("list")
    def vertical_list(
        root: Path = typer.Option(Path.cwd(), "--root", help="Optional project root for local packs"),
        source: str = typer.Option(
            "local",
            "--source",
            help="Catalog source: local, remote or all",
        ),
        registry: str = typer.Option("", "--registry", help="Configured remote registry"),
        include_private: bool = typer.Option(
            False,
            "--include-private",
            help="Include authorized private remote releases",
        ),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
    ) -> None:
        """List exact vertical releases without implicit remote access."""
        try:
            normalized_source = source.strip().lower()
            if normalized_source not in {"local", "remote", "all"}:
                raise ValueError("P2P_VERTICAL_INVALID_SOURCE: source must be local, remote or all")
            client = VerticalRegistryClient() if normalized_source in {"remote", "all"} else None
            catalog = VerticalCatalogService(root, client=client)
            local = catalog.local_items() if normalized_source in {"local", "all"} else ()
            remote = (
                catalog.remote_items(
                    registry=registry,
                    include_private=include_private,
                )
                if normalized_source in {"remote", "all"}
                else ()
            )
            items = (*local, *remote)
        except ValueError as exc:
            _operation_error("vertical.list", exc, output_format)
        data = {"source": normalized_source, "verticals": items}
        if _wants_json(output_format):
            print_json(success_envelope("vertical.list", data))
            return
        console.print(f"Vertical releases ({normalized_source})")
        for item in items:
            console.print(f"  {item.coordinate}  {item.source}  {item.visibility}  {item.name}")

    @vertical_app.command("search")
    def vertical_search(
        query: str = typer.Argument(..., help="Catalog search terms"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Optional project root"),
        registry: str = typer.Option("", "--registry", help="Configured remote registry"),
        include_private: bool = typer.Option(False, "--include-private"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
    ) -> None:
        """Search local and selected remote vertical metadata."""
        try:
            items = VerticalCatalogService(
                root,
                client=VerticalRegistryClient(),
            ).search(
                query,
                registry=registry,
                include_private=include_private,
            )
        except ValueError as exc:
            _operation_error("vertical.search", exc, output_format)
        data = {"query": query, "verticals": items}
        if _wants_json(output_format):
            print_json(success_envelope("vertical.search", data))
            return
        for item in items:
            availability = "local" if item.local_available else "remote"
            console.print(
                f"  {item.coordinate}  {item.visibility}  {availability}  {item.name}"
            )

    @vertical_app.command("pull")
    def vertical_pull(
        coordinate: str = typer.Argument(..., help="Exact publisher/id@version coordinate"),
        registry: str = typer.Option("", "--registry", help="Configured remote registry"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
    ) -> None:
        """Pull and verify one exact release and its dependency closure."""
        try:
            result = VerticalPullService().pull(coordinate, registry=registry)
        except ValueError as exc:
            _operation_error("vertical.pull", exc, output_format)
        if _wants_json(output_format):
            print_json(success_envelope("vertical.pull", result))
            return
        console.print(f"[green]Vertical {result.status}.[/green] {result.requested_coordinate}")
        for item in result.releases:
            console.print(f"  {item.release.coordinate}  {item.artifact_path}")

    @vertical_app.command("inspect")
    def vertical_inspect(
        target: str = typer.Argument(..., help="Exact local coordinate or portable artifact path"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Optional project root"),
        output_format: str = typer.Option("json", "--format", help="Output format: text or json"),
    ) -> None:
        """Inspect one exact local release or portable artifact."""
        source = Path(target)
        try:
            catalog = VerticalCatalogService(root)
            workspace = catalog.workspace
            if source.exists() or (not source.is_absolute() and (root / source).exists()):
                inspection = workspace.inspect_portable_vertical(source, view="effective")
                data: object = {
                    "target": inspection.target,
                    "coordinate": inspection.pack.coordinate,
                    "artifact_checksum": inspection.artifact_checksum,
                    "semantic_checksum": inspection.semantic_checksum,
                    "pack": inspection.effective_payload,
                }
            else:
                item = catalog.resolve(target)
                if item.artifact_path is not None:
                    inspection = catalog.inspect_cached(item)
                    data = {
                        "target": target,
                        "coordinate": inspection.pack.coordinate,
                        "artifact_checksum": inspection.artifact_checksum,
                        "semantic_checksum": inspection.semantic_checksum,
                        "source": item.source,
                        "registry": item.registry,
                        "pack": inspection.effective_payload,
                    }
                else:
                    pack = workspace.show_project_vertical(target)
                    data = {
                        "target": target,
                        "coordinate": pack.coordinate,
                        "source": item.source,
                        "pack": pack,
                    }
        except ValueError as exc:
            _operation_error("vertical.inspect", exc, output_format)
        if _wants_json(output_format):
            print_json(success_envelope("vertical.inspect", data))
            return
        console.print(f"Vertical release: {data['coordinate']}")

    @registry_app.command("list")
    def registry_list(
        refresh: bool = typer.Option(
            False,
            "--refresh",
            help="Explicitly refresh remote protocol capabilities",
        ),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
    ) -> None:
        """List configured registries without network access."""
        try:
            service = VerticalRegistryConfigurationService()
            result = service.read()
            if refresh:
                client = VerticalRegistryClient(configuration=service)
                for item in result.registries:
                    client.capabilities(item.name, refresh=True)
                result = service.read()
        except ValueError as exc:
            _operation_error("vertical.registry.list", exc, output_format)
        if _wants_json(output_format):
            print_json(success_envelope("vertical.registry.list", result))
            return
        console.print("Vertical registries")
        if not result.registries:
            console.print("  none")
            return
        for item in result.registries:
            marker = "*" if item.name == result.default_registry else " "
            negotiated = item.capabilities.protocol_version if item.capabilities else "not-negotiated"
            console.print(f"  {marker} {item.name}  {item.url}  {negotiated}")

    @registry_app.command("add")
    def registry_add(
        name: str = typer.Argument(..., help="Local registry name"),
        url: str = typer.Argument(..., help="HTTPS registry base URL"),
        make_default: bool = typer.Option(False, "--default", help="Make this the default registry"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
    ) -> None:
        """Add an idempotent local registry configuration."""
        try:
            result = VerticalRegistryConfigurationService().add(
                name,
                url,
                make_default=make_default,
            )
        except ValueError as exc:
            _operation_error("vertical.registry.add", exc, output_format)
        if _wants_json(output_format):
            print_json(success_envelope("vertical.registry.add", result))
            return
        console.print(f"[green]Registry configured.[/green] {name}")

    @registry_app.command("remove")
    def registry_remove(
        name: str = typer.Argument(..., help="Configured registry name"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
    ) -> None:
        """Remove local registry configuration without deleting cached packs."""
        try:
            result = VerticalRegistryConfigurationService().remove(name)
        except ValueError as exc:
            _operation_error("vertical.registry.remove", exc, output_format)
        if _wants_json(output_format):
            print_json(success_envelope("vertical.registry.remove", result))
            return
        console.print(f"[green]Registry removed.[/green] {name}")

    @vertical_app.command("login")
    def vertical_login(
        registry: str = typer.Argument("", help="Configured registry; defaults to selected registry"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
    ) -> None:
        """Authenticate through the registry-advertised OAuth device flow."""
        try:
            client = VerticalRegistryClient()
            registry_name, authorization = client.start_login(registry)
            message = (
                f"Open {authorization.verification_uri} and enter code "
                f"{authorization.user_code}"
            )
            if _wants_json(output_format):
                typer.echo(message, err=True)
            else:
                console.print(message)
            credential = client.complete_login(registry_name, authorization)
            data = {
                "registry": registry_name,
                "authorization": authorization.public_dict(),
                "credential": credential.public_dict(),
            }
        except ValueError as exc:
            _operation_error("vertical.login", exc, output_format)
        if _wants_json(output_format):
            print_json(success_envelope("vertical.login", data))
            return
        console.print(f"[green]Registry login completed.[/green] {registry_name}")

    @vertical_app.command("logout")
    def vertical_logout(
        registry: str = typer.Argument("", help="Configured registry; defaults to selected registry"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
    ) -> None:
        """Delete locally stored registry credentials."""
        try:
            registry_name, removed = VerticalRegistryClient().logout(registry)
        except ValueError as exc:
            _operation_error("vertical.logout", exc, output_format)
        data = {"registry": registry_name, "removed": removed}
        if _wants_json(output_format):
            print_json(success_envelope("vertical.logout", data))
            return
        status = "removed" if removed else "not present"
        console.print(f"Registry credential {status}: {registry_name}")


def _wants_json(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized not in {"text", "json"}:
        raise typer.BadParameter("Output format must be text or json.")
    return normalized == "json"


def _operation_error(operation: str, exc: ValueError, output_format: str) -> None:
    if _wants_json(output_format):
        message = str(exc)
        prefix = message.split(":", 1)[0]
        code = prefix if prefix.startswith("P2P_") else "P2P_VERTICAL_OPERATION_FAILED"
        print_json(error_envelope(operation, code=code, message=message))
        raise typer.Exit(1)
    fail(str(exc))


def _load_draft_document(path: Path) -> dict[str, object]:
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"P2P_VERTICAL_DRAFT_DOCUMENT_NOT_FOUND: {path}")
    try:
        size = path.stat().st_size
        if size > VERTICAL_DRAFT_MAX_DOCUMENT_BYTES:
            raise ValueError("P2P_VERTICAL_DRAFT_LIMIT: document is too large")
        payload = load_yaml(path.read_bytes())
    except OSError as exc:
        raise ValueError(f"P2P_VERTICAL_DRAFT_DOCUMENT_INVALID: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("P2P_VERTICAL_DRAFT_DOCUMENT_INVALID: expected a mapping")
    return {str(key): value for key, value in payload.items()}


def _draft_output(operation: str, result: object, output_format: str) -> None:
    payload = result.to_dict() if hasattr(result, "to_dict") else result
    if _wants_json(output_format):
        print_json(success_envelope(operation, payload))
        return
    mapping = payload if isinstance(payload, dict) else {}
    draft = mapping.get("draft", {})
    assessment = mapping.get("assessment", {})
    console.print(
        f"[green]{operation} completed.[/green] "
        f"{draft.get('draft_id', '')} revision={draft.get('revision', '')} "
        f"readiness={assessment.get('readiness', '')}%"
    )
