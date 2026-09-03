from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
from typer.testing import CliRunner

from p2p_engine.cli import app
from p2p_engine.core.canonical_memory import canonical_json_bytes
from p2p_engine.core.linked_replica import ReplicaAccessState, ReplicaFreshness
from p2p_engine.core.project_identity import AuthorityEpoch, RemoteProjectId, ReplicaId
from p2p_engine.core.project_replication import (
    ChangeBatch,
    ChangeBlobReference,
    ChangeFeed,
    EntityPrecondition,
    ProjectCommand,
    ProjectNotification,
    batch_from_mapping,
    command_from_mapping,
    feed_from_mapping,
    receipt_from_mapping,
    replication_entity_version,
)
from p2p_engine.mcp.registry import TOOL_NAMES
from p2p_engine.mcp.tools import call_tool
from p2p_engine.services.canonical_memory import CanonicalBundleCodec
from p2p_engine.services.linked_replica import LinkedReplicaService
from p2p_engine.services.project_application import ProjectApplicationService
from p2p_engine.services.project_replication import FilesystemProjectReplicationStore
from p2p_engine.storage.canonical_memory import FilesystemCanonicalMemoryStore
from p2p_engine.storage.filesystem_linked_replica import FilesystemLinkedReplicaStore
from tests.test_linked_replica import (
    PROFILE,
    REMOTE_ID,
    SERVER,
    FakeIntegration,
    FakeReplicaTransport,
    _capabilities,
    _credentials,
)

runner = CliRunner()


class FakeDurableTransport(FakeReplicaTransport):
    def __init__(self, bundle: bytes, snapshot: object, *, batch, receipt) -> None:
        super().__init__(bundle, snapshot)
        self.batch = batch
        self.receipt = receipt
        self.lose_command_response = False
        self.defer_feed_until_command = False
        self.command_issued = False
        self.notifications = [
            ProjectNotification(
                event_id="evt_revision_2",
                kind="project.revision.available",
                project_uuid=batch.project_uuid,
                project_revision=batch.project_revision,
                change_batch_id=batch.change_batch_id,
                operation_id=batch.operation_id,
            ).to_dict()
        ]

    def request_json(self, method: str, url: str, **kwargs: object) -> object:
        if url.endswith("/.well-known/p2p-linked-replica"):
            payload = _capabilities()
            body = payload["linked_replica_capabilities"]
            assert isinstance(body, dict)
            body["replication"] = {
                "protocol": "p2p-durable-replication/v1",
                "endpoints": {
                    "command": "/api/projects/{remote_project_id}/commands",
                    "operation": "/api/projects/{remote_project_id}/operations/{operation_id}",
                    "feed": "/api/project-replicas/{replica_id}/feed",
                    "blob": "/api/project-replicas/{replica_id}/blobs/{digest}",
                    "events": "/api/project-replicas/{replica_id}/events",
                },
                "limits": {
                    "max_command_bytes": 1_048_576,
                    "max_batch_bytes": 8_388_608,
                    "max_page_batches": 64,
                },
                "heartbeat_seconds": 30,
            }
            return payload
        if method == "GET" and urlsplit(url).path.endswith("/feed"):
            after = int(parse_qs(urlsplit(url).query)["after_revision"][0])
            visible = not self.defer_feed_until_command or self.command_issued
            batches = (
                (self.batch,) if visible and after < self.batch.project_revision else ()
            )
            current_revision = self.batch.project_revision if visible else after
            return {
                "project_change_feed": ChangeFeed(
                    status="changes" if batches else "up-to-date",
                    project_uuid=self.batch.project_uuid,
                    replica_id=ReplicaId(self.replica_id),
                    authority_epoch=self.batch.authority_epoch,
                    after_revision=after,
                    oldest_available_revision=2,
                    current_revision=current_revision,
                    batches=batches,
                    has_more=False,
                ).to_dict()
            }
        if method == "POST" and urlsplit(url).path.endswith("/commands"):
            self.command_issued = True
            if self.lose_command_response:
                raise ValueError("P2P_WAVEKIT_RESPONSE_UNKNOWN: simulated lost response")
            return {"operation_receipt": self.receipt.to_dict()}
        if method == "GET" and "/operations/" in urlsplit(url).path:
            return {
                "operation_status": {
                    "contract": "p2p-project-operation-status/v1",
                    "operation_id": self.receipt.operation_id,
                    "receipt": self.receipt.to_dict(),
                }
            }
        return super().request_json(method, url, **kwargs)

    def iter_sse(self, *args: object, **kwargs: object):
        yield from self.notifications


def _command(
    root: Path,
    *,
    operation_id: str,
    revision: int,
    idempotency_key: str | None = None,
    authority_epoch: int = 2,
    payload: dict[str, object] | None = None,
    entity_preconditions: tuple[EntityPrecondition, ...] = (),
    command_name: str = "project.domain.set",
    payload_contract: str = "p2p-project-domain-set/v1",
) -> tuple[ProjectCommand, Path]:
    identity = ProjectApplicationService(root).project_identity()
    command = ProjectCommand(
        operation_id=operation_id,
        idempotency_key=idempotency_key or f"key:{operation_id}",
        project_uuid=identity.project_uuid,
        remote_project_id=RemoteProjectId(REMOTE_ID),
        replica_id=ReplicaId("50f0a643-50aa-4a08-99ce-a0946f9951c1"),
        authority_epoch=AuthorityEpoch(authority_epoch),
        expected_project_revision=revision,
        entity_preconditions=entity_preconditions,
        command=command_name,
        payload_contract=payload_contract,
        payload=payload or {"key": "software", "name": "Software"},
    )
    path = root.parent / f"{operation_id}.json"
    path.write_bytes(canonical_json_bytes(command.to_dict()))
    return command, path


def _mutate_domain(root: Path, command_path: Path, *, operation_key: str):
    return runner.invoke(
        app,
        [
            "--replication-command-envelope",
            str(command_path),
            "project",
            "domain",
            "set",
            "software",
            "--name",
            "Software",
            "--actor",
            "owner",
            "--operation-key",
            operation_key,
            "--format",
            "json",
            "--root",
            str(root),
        ],
    )


def _mutate_structure(root: Path, command_path: Path, *, operation_key: str):
    return runner.invoke(
        app,
        [
            "--replication-command-envelope",
            str(command_path),
            "project",
            "structure",
            "add-section",
            "Notes",
            "--expected-revision",
            "1",
            "--actor",
            "owner",
            "--operation-key",
            operation_key,
            "--format",
            "json",
            "--root",
            str(root),
        ],
    )


def _durable_scenario(tmp_path: Path):
    server = tmp_path / "server"
    ProjectApplicationService(server).init_project("Replication", starter_id="empty")
    baseline = ProjectApplicationService(server).canonical_memory_snapshot()
    bundle_path = tmp_path / "baseline.p2pbundle"
    ProjectApplicationService(server).canonical_bundle_export(bundle_path)
    bundle = bundle_path.read_bytes()
    store = FilesystemProjectReplicationStore(server)
    store.initialize(authority_epoch=2, project_revision=1)
    command, command_path = _command(server, operation_id="op_domain_1", revision=1)
    assert _mutate_domain(server, command_path, operation_key="wavekit-domain-op-1").exit_code == 0
    batch = store.feed(after_revision=1, replica_id=command.replica_id.value).batches[0]
    receipt = store.receipt(command.operation_id)
    assert receipt is not None
    target = tmp_path / "client"
    transport = FakeDurableTransport(bundle, baseline, batch=batch, receipt=receipt)
    LinkedReplicaService(
        root=target,
        transport=transport,
        credentials=_credentials(),
        integration_transition=lambda: FakeIntegration(),
        now=lambda: 1_900_000_000,
    ).clone(
        server_url=SERVER,
        remote_project_id=REMOTE_ID,
        account_profile_ref=PROFILE,
        operation_key="owner:clone:durable",
        confirm=True,
    )
    return server, target, command, batch, receipt, transport


@pytest.mark.unit
def test_replication_contracts_round_trip_and_reject_digest_tampering(tmp_path: Path) -> None:
    root = tmp_path / "project"
    ProjectApplicationService(root).init_project("Replication", starter_id="empty")
    command, _path = _command(root, operation_id="op_contract_1", revision=1)

    assert command_from_mapping(command.to_dict()) == command
    with pytest.raises(ValueError, match="fields are not exact"):
        command_from_mapping({**command.to_dict(), "actor": "untrusted"})

    non_json = runner.invoke(
        app,
        [
            "--replication-command-envelope",
            str(_path),
            "project",
            "domain",
            "show",
            "--root",
            str(root),
        ],
    )
    assert non_json.exit_code == 2
    assert "P2P_REPLICATION_WORKER_JSON_REQUIRED" in non_json.stdout


@pytest.mark.integration
def test_worker_mutation_commits_state_receipt_and_backend_neutral_batch_atomically(
    tmp_path: Path,
) -> None:
    root = tmp_path / "server-project"
    ProjectApplicationService(root).init_project("Replication", starter_id="empty")
    store = FilesystemProjectReplicationStore(root)
    store.initialize(authority_epoch=2, project_revision=1, retention_batches=8)
    command, command_path = _command(root, operation_id="op_domain_1", revision=1)

    result = _mutate_domain(root, command_path, operation_key="wavekit-domain-op-1")

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    receipt = receipt_from_mapping(payload["data"]["replication_receipt"])
    assert receipt.operation_id == command.operation_id
    assert receipt.base_project_revision == 1
    assert receipt.project_revision == 2
    state = store.state()
    assert state is not None and state.current_revision == 2
    persisted = store.receipt(command.operation_id)
    assert persisted == receipt
    feed = store.feed(
        after_revision=1,
        replica_id=command.replica_id.value,
        limit=8,
    )
    assert feed.status == "changes"
    assert feed.to_revision == 2
    batch = feed.batches[0]
    assert batch_from_mapping(batch.to_dict()) == batch
    serialized = json.dumps(batch.to_dict(), sort_keys=True)
    assert ".p2p/" not in serialized
    assert "storage_locator" not in serialized
    assert "sql" not in serialized.lower()


@pytest.mark.cli
def test_worker_replication_and_local_sync_status_cli_are_versioned(tmp_path: Path) -> None:
    server = tmp_path / "server-project"
    ProjectApplicationService(server).init_project("Replication", starter_id="empty")
    initialized = runner.invoke(
        app,
        [
            "project",
            "replication",
            "initialize",
            "--authority-epoch",
            "2",
            "--project-revision",
            "1",
            "--retention-batches",
            "8",
            "--confirm",
            "--format",
            "json",
            "--root",
            str(server),
        ],
    )
    assert initialized.exit_code == 0, initialized.stdout
    assert json.loads(initialized.stdout)["operation"] == "project.replication.initialize"
    status = runner.invoke(
        app,
        [
            "project",
            "replication",
            "status",
            "--format",
            "json",
            "--root",
            str(server),
        ],
    )
    feed = runner.invoke(
        app,
        [
            "project",
            "replication",
            "feed",
            "--after-revision",
            "1",
            "--replica-id",
            "50f0a643-50aa-4a08-99ce-a0946f9951c1",
            "--format",
            "json",
            "--root",
            str(server),
        ],
    )
    assert status.exit_code == 0
    assert feed.exit_code == 0
    assert json.loads(status.stdout)["operation"] == "project.replication.status"
    assert json.loads(feed.stdout)["data"]["project_change_feed"]["status"] == (
        "up-to-date"
    )


@pytest.mark.integration
def test_stale_project_revision_does_not_mutate_or_advance_feed(tmp_path: Path) -> None:
    root = tmp_path / "server-project"
    ProjectApplicationService(root).init_project("Replication", starter_id="empty")
    store = FilesystemProjectReplicationStore(root)
    store.initialize(authority_epoch=2, project_revision=1)
    _first, first_path = _command(root, operation_id="op_domain_1", revision=1)
    assert _mutate_domain(root, first_path, operation_key="wavekit-domain-op-1").exit_code == 0
    _stale, stale_path = _command(root, operation_id="op_domain_stale", revision=1)

    stale = _mutate_domain(root, stale_path, operation_key="wavekit-domain-op-stale")

    assert stale.exit_code != 0
    assert "P2P_REPLICATION_REVISION_CONFLICT" in stale.stdout
    state = store.state()
    assert state is not None and state.current_revision == 2
    assert store.receipt("op_domain_stale") is None


@pytest.mark.integration
def test_operation_and_idempotency_identity_cannot_be_reused_for_other_work(
    tmp_path: Path,
) -> None:
    root = tmp_path / "server-project"
    ProjectApplicationService(root).init_project("Replication", starter_id="empty")
    store = FilesystemProjectReplicationStore(root)
    store.initialize(authority_epoch=2, project_revision=1)
    command, command_path = _command(root, operation_id="op_domain_1", revision=1)
    first = _mutate_domain(root, command_path, operation_key="wavekit-domain-op-1")
    assert first.exit_code == 0
    first_receipt = store.receipt(command.operation_id)
    replay = _mutate_domain(root, command_path, operation_key="wavekit-domain-op-retry")
    assert replay.exit_code == 0, replay.stdout
    assert store.receipt(command.operation_id) == first_receipt
    assert store.state() is not None and store.state().current_revision == 2

    _changed, changed_path = _command(
        root,
        operation_id=command.operation_id,
        revision=1,
        idempotency_key=command.idempotency_key,
        payload={"key": "software", "name": "A different command"},
    )
    changed = _mutate_domain(root, changed_path, operation_key="wavekit-domain-op-2")
    assert changed.exit_code != 0
    assert "P2P_REPLICATION_OPERATION_CONFLICT" in changed.stdout

    _other, other_path = _command(
        root,
        operation_id="op_domain_2",
        revision=2,
        idempotency_key=command.idempotency_key,
    )
    other = _mutate_domain(root, other_path, operation_key="wavekit-domain-op-3")
    assert other.exit_code != 0
    assert "P2P_REPLICATION_IDEMPOTENCY_CONFLICT" in other.stdout
    state = store.state()
    assert state is not None and state.current_revision == 2


@pytest.mark.integration
def test_authority_epoch_change_fails_before_canonical_commit(tmp_path: Path) -> None:
    root = tmp_path / "server-project"
    ProjectApplicationService(root).init_project("Replication", starter_id="empty")
    store = FilesystemProjectReplicationStore(root)
    store.initialize(authority_epoch=3, project_revision=1)
    _command_value, command_path = _command(
        root,
        operation_id="op_old_authority",
        revision=1,
        authority_epoch=2,
    )

    result = _mutate_domain(root, command_path, operation_key="wavekit-old-authority")

    assert result.exit_code != 0
    assert "P2P_REPLICATION_AUTHORITY_CHANGED" in result.stdout
    assert store.receipt("op_old_authority") is None
    assert store.state() is not None and store.state().current_revision == 1


@pytest.mark.integration
def test_stale_same_entity_conflicts_but_unaffected_entity_can_commit(
    tmp_path: Path,
) -> None:
    root = tmp_path / "server-project"
    application = ProjectApplicationService(root)
    application.init_project("Replication", starter_id="empty")
    initial = CanonicalBundleCodec().snapshot(FilesystemCanonicalMemoryStore(root))
    initial_entities = {
        (item.entity_type, item.technical_id): item for item in initial.entities
    }

    def version(kind: str, entity_id: str) -> int:
        entity = initial_entities[(kind, entity_id)]
        return replication_entity_version(
            kind=entity.entity_type,
            entity_id=entity.technical_id,
            payload_contract="p2p-canonical-memory/v1",
            payload=entity.payload,
        )

    store = FilesystemProjectReplicationStore(root)
    store.initialize(authority_epoch=2, project_revision=1)
    _first, first_path = _command(root, operation_id="op_domain_1", revision=1)
    assert _mutate_domain(root, first_path, operation_key="wavekit-domain-op-1").exit_code == 0

    _same, same_path = _command(
        root,
        operation_id="op_domain_same",
        revision=1,
        entity_preconditions=(
            EntityPrecondition("project.domain", "project:domain", 0),
        ),
    )
    same = _mutate_domain(root, same_path, operation_key="wavekit-domain-op-same")
    assert same.exit_code != 0
    assert "P2P_REPLICATION_ENTITY_CONFLICT" in same.stdout

    independent, independent_path = _command(
        root,
        operation_id="op_structure_independent",
        revision=1,
        entity_preconditions=(
            EntityPrecondition(
                "p2p.project.structure",
                "project:structure",
                version("p2p.project.structure", "project:structure"),
            ),
            EntityPrecondition(
                "p2p.project.structure-events",
                "project:structure-events",
                version("p2p.project.structure-events", "project:structure-events"),
            ),
            EntityPrecondition(
                "p2p.project.structure-snapshots",
                "project:structure-snapshots",
                0,
            ),
        ),
        command_name="project.structure.add-section",
        payload_contract="p2p-project-structure-add-section/v1",
        payload={"title": "Notes", "expected_structure_revision": 1},
    )
    result = _mutate_structure(
        root,
        independent_path,
        operation_key="wavekit-structure-independent",
    )
    assert result.exit_code == 0, result.stdout
    receipt = store.receipt(independent.operation_id)

    assert receipt is not None
    assert receipt.base_project_revision == 2
    assert receipt.project_revision == 3
    assert store.state() is not None and store.state().current_revision == 3


@pytest.mark.integration
def test_change_batch_converges_clone_and_duplicate_is_harmless(tmp_path: Path) -> None:
    server = tmp_path / "server"
    ProjectApplicationService(server).init_project("Replication", starter_id="empty")
    baseline = ProjectApplicationService(server).canonical_memory_snapshot()
    bundle_path = tmp_path / "baseline.p2pbundle"
    ProjectApplicationService(server).canonical_bundle_export(bundle_path)
    bundle = bundle_path.read_bytes()
    replication = FilesystemProjectReplicationStore(server)
    replication.initialize(authority_epoch=2, project_revision=1)

    target = tmp_path / "client"
    transport = FakeReplicaTransport(bundle, baseline)
    LinkedReplicaService(
        root=target,
        transport=transport,
        credentials=_credentials(),
        integration_transition=lambda: FakeIntegration(),
        now=lambda: 1_900_000_000,
    ).clone(
        server_url=SERVER,
        remote_project_id=REMOTE_ID,
        account_profile_ref=PROFILE,
        operation_key="owner:clone:durable",
        confirm=True,
    )
    command, command_path = _command(server, operation_id="op_domain_1", revision=1)
    assert _mutate_domain(server, command_path, operation_key="wavekit-domain-op-1").exit_code == 0
    batch = replication.feed(
        after_revision=1, replica_id=command.replica_id.value
    ).batches[0]
    local_store = FilesystemLinkedReplicaStore(target)

    applied = local_store.apply_change_batch(batch, blob_bytes={}, verified_at=1_900_000_100)
    replayed = local_store.apply_change_batch(batch, blob_bytes={}, verified_at=1_900_000_200)

    server_snapshot = CanonicalBundleCodec().snapshot(FilesystemCanonicalMemoryStore(server))
    client_snapshot = CanonicalBundleCodec().snapshot(FilesystemCanonicalMemoryStore(target))
    assert applied.last_applied_revision == 2
    assert replayed.last_applied_revision == 2
    assert client_snapshot.semantic_state_digest == server_snapshot.semantic_state_digest


@pytest.mark.integration
def test_compaction_reports_retention_gap_without_deleting_receipt(tmp_path: Path) -> None:
    root = tmp_path / "server-project"
    ProjectApplicationService(root).init_project("Replication", starter_id="empty")
    store = FilesystemProjectReplicationStore(root)
    store.initialize(authority_epoch=2, project_revision=1)
    command, command_path = _command(root, operation_id="op_domain_1", revision=1)
    assert _mutate_domain(root, command_path, operation_key="wavekit-domain-op-1").exit_code == 0

    store.compact(retain_after_revision=2)
    gap = store.feed(after_revision=1, replica_id=command.replica_id.value)

    assert feed_from_mapping(gap.to_dict()) == gap
    assert gap.status == "retention-gap"
    assert gap.snapshot == {
        "required": True,
        "reason": "cursor is older than retained project changes",
    }
    assert store.receipt(command.operation_id) is not None


@pytest.mark.unit
def test_entity_preconditions_are_ordered_and_unique() -> None:
    one = EntityPrecondition("proposal", "PROP-1", 2)
    two = EntityPrecondition("proposal", "PROP-2", 1)
    assert tuple(sorted((two, one))) == (one, two)


@pytest.mark.integration
def test_http_feed_converges_without_any_realtime_notification(tmp_path: Path) -> None:
    server, target, _command_value, _batch, _receipt, transport = _durable_scenario(
        tmp_path
    )
    transport.notifications = []
    service = LinkedReplicaService(
        root=target,
        transport=transport,
        credentials=_credentials(),
        integration_transition=lambda: FakeIntegration(),
        now=lambda: 1_900_000_100,
    )

    result = service.catch_up()

    assert result.status == "caught-up"
    assert result.binding.last_applied_revision == 2
    assert ProjectApplicationService(target).canonical_memory_snapshot().semantic_state_digest == (
        ProjectApplicationService(server).canonical_memory_snapshot().semantic_state_digest
    )


@pytest.mark.integration
def test_lost_command_response_recovers_receipt_then_applies_feed(tmp_path: Path) -> None:
    _server, target, command, _batch, receipt, transport = _durable_scenario(tmp_path)
    transport.lose_command_response = True
    transport.defer_feed_until_command = True
    service = LinkedReplicaService(
        root=target,
        transport=transport,
        credentials=_credentials(),
        integration_transition=lambda: FakeIntegration(),
        now=lambda: 1_900_000_100,
    )

    result = service.submit_command(
        operation_id=command.operation_id,
        idempotency_key=command.idempotency_key,
        command=command.command,
        payload_contract=command.payload_contract,
        payload=command.payload,
    )

    assert result["receipt"] == receipt.to_dict()
    assert result["freshness"]["last_applied_revision"] == 2


@pytest.mark.integration
def test_sse_notification_is_only_a_wakeup_for_durable_catch_up(tmp_path: Path) -> None:
    _server, target, _command_value, batch, _receipt, transport = _durable_scenario(
        tmp_path
    )
    service = LinkedReplicaService(
        root=target,
        transport=transport,
        credentials=_credentials(),
        integration_transition=lambda: FakeIntegration(),
        now=lambda: 1_900_000_100,
    )

    events = service.watch(max_events=1)

    assert events[0]["notification"]["change_batch_id"] == batch.change_batch_id
    assert events[0]["freshness"]["last_applied_revision"] == 2


def test_watch_cli_streams_text_and_bounds_single_document_json(monkeypatch) -> None:
    class FakeWatchService:
        def __init__(self, *, root: Path) -> None:
            assert root == Path.cwd()

        def iter_watch(self, *, max_events: int = 0):
            assert max_events == 2
            for revision in (7, 8):
                yield {
                    "notification": {"project_revision": revision},
                    "freshness": {"project_revision": revision},
                }

    monkeypatch.setattr(
        "p2p_engine.cli_commands.linked_replica.LinkedReplicaService",
        FakeWatchService,
    )
    text_result = runner.invoke(app, ["watch", "--max-events", "2"])
    assert text_result.exit_code == 0
    assert "Project revision 7 is available" in text_result.stdout
    assert "Project revision 8 is available" in text_result.stdout
    assert "Stopped after 2 project notification(s)." in text_result.stdout

    json_result = runner.invoke(app, ["watch", "--format", "json"])
    assert json_result.exit_code != 0
    payload = json.loads(json_result.stdout)
    assert payload["error"]["code"] == "P2P_REPLICATION_WATCH_BOUND_REQUIRED"


def test_normal_cli_read_preflights_once_and_reports_linked_freshness(
    tmp_path: Path, monkeypatch
) -> None:
    _server, target, _command_value, _batch, _receipt, _transport = _durable_scenario(
        tmp_path
    )
    calls: list[bool] = []
    freshness = ReplicaFreshness(
        state=ReplicaAccessState.active,
        source="remote",
        stale=False,
        last_applied_revision=2,
        cursor=2,
        last_verified_at=1_900_000_100,
        writes_permitted=True,
    )

    def preflight(self, *, mutation: bool):
        calls.append(mutation)
        return freshness

    monkeypatch.setattr(
        ProjectApplicationService,
        "linked_replica_before_operation",
        preflight,
    )
    result = runner.invoke(
        app,
        ["project", "domain", "show", "--root", str(target), "--format", "json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert calls == [False]
    assert payload["data"]["linked_replica_freshness"] == freshness.to_dict()

    status = runner.invoke(
        app,
        ["sync", "status", "--root", str(target), "--format", "json"],
    )
    assert status.exit_code == 0
    assert calls == [False]


@pytest.mark.integration
def test_interrupted_local_apply_rolls_back_state_inbox_and_cursor(tmp_path: Path) -> None:
    _server, target, _command_value, batch, _receipt, _transport = _durable_scenario(
        tmp_path
    )
    before = ProjectApplicationService(target).canonical_memory_snapshot()
    before_binding = FilesystemLinkedReplicaStore(target).load()
    assert before_binding is not None
    raised = False

    def interrupt(stage: str, target_path: str) -> None:
        nonlocal raised
        if stage == "after_replace" and not raised:
            raised = True
            raise RuntimeError(f"simulated interruption after {target_path}")

    store = FilesystemLinkedReplicaStore(target, failure_injector=interrupt)
    with pytest.raises(ValueError, match="P2P_LINKED_REPLICA_LOCAL_COMMIT_FAILED"):
        store.apply_change_batch(batch, blob_bytes={}, verified_at=1_900_000_100)

    after_binding = FilesystemLinkedReplicaStore(target).load()
    after = ProjectApplicationService(target).canonical_memory_snapshot()
    assert after_binding == before_binding
    assert after.semantic_state_digest == before.semantic_state_digest
    assert not (
        target
        / ".p2p"
        / "local"
        / "project-replication"
        / "inbox"
        / f"{batch.batch_digest}.json"
    ).exists()


@pytest.mark.integration
def test_missing_blob_never_advances_cursor_or_commits_entity_state(tmp_path: Path) -> None:
    _server, target, _command_value, batch, _receipt, _transport = _durable_scenario(
        tmp_path
    )
    before = ProjectApplicationService(target).canonical_memory_snapshot()
    before_binding = FilesystemLinkedReplicaStore(target).load()
    assert before_binding is not None
    missing_blob_batch = ChangeBatch(
        change_batch_id="chg_missing_blob",
        project_uuid=batch.project_uuid,
        authority_epoch=batch.authority_epoch,
        previous_revision=batch.previous_revision,
        project_revision=batch.project_revision,
        operation_id=batch.operation_id,
        upserts=batch.upserts,
        tombstones=batch.tombstones,
        blob_references=(ChangeBlobReference("0" * 64, 4),),
        semantic_state_digest=batch.semantic_state_digest,
        blob_manifest_digest=batch.blob_manifest_digest,
    )

    with pytest.raises(ValueError, match="P2P_REPLICATION_BLOB_MISSING"):
        FilesystemLinkedReplicaStore(target).apply_change_batch(
            missing_blob_batch,
            blob_bytes={},
            verified_at=1_900_000_100,
        )

    assert FilesystemLinkedReplicaStore(target).load() == before_binding
    assert (
        ProjectApplicationService(target).canonical_memory_snapshot().semantic_state_digest
        == before.semantic_state_digest
    )


@pytest.mark.integration
def test_duplicate_and_reordered_notifications_still_follow_the_feed(tmp_path: Path) -> None:
    _server, target, _command_value, batch, _receipt, transport = _durable_scenario(
        tmp_path
    )
    later_hint = ProjectNotification(
        event_id="evt_later_hint",
        kind="project.revision.available",
        project_uuid=batch.project_uuid,
        project_revision=batch.project_revision + 10,
        change_batch_id="chg_unconfirmed_hint",
        operation_id="op_unconfirmed_hint",
    ).to_dict()
    transport.notifications = [later_hint, transport.notifications[0], later_hint]
    service = LinkedReplicaService(
        root=target,
        transport=transport,
        credentials=_credentials(),
        integration_transition=lambda: FakeIntegration(),
        now=lambda: 1_900_000_100,
    )

    events = service.watch(max_events=3)

    assert len(events) == 3
    assert all(item["freshness"]["last_applied_revision"] == 2 for item in events)
    assert FilesystemLinkedReplicaStore(target).load().last_applied_revision == 2


@pytest.mark.integration
def test_feed_rejects_gaps_and_false_pagination_flags(tmp_path: Path) -> None:
    _server, _target, _command_value, batch, _receipt, _transport = _durable_scenario(
        tmp_path
    )
    with pytest.raises(ValueError, match="P2P_REPLICATION_CURSOR_GAP"):
        ChangeFeed(
            status="changes",
            project_uuid=batch.project_uuid,
            replica_id=ReplicaId("50f0a643-50aa-4a08-99ce-a0946f9951c1"),
            authority_epoch=batch.authority_epoch,
            after_revision=0,
            oldest_available_revision=1,
            current_revision=2,
            batches=(batch,),
            has_more=False,
        )
    with pytest.raises(ValueError, match="pagination flag"):
        ChangeFeed(
            status="changes",
            project_uuid=batch.project_uuid,
            replica_id=ReplicaId("50f0a643-50aa-4a08-99ce-a0946f9951c1"),
            authority_epoch=batch.authority_epoch,
            after_revision=1,
            oldest_available_revision=2,
            current_revision=3,
            batches=(batch,),
            has_more=False,
        )


@pytest.mark.integration
def test_ephemeral_presence_and_replication_local_state_are_not_bundled(
    tmp_path: Path,
) -> None:
    _server, target, _command_value, _batch, _receipt, _transport = _durable_scenario(
        tmp_path
    )
    presence = (
        target
        / ".p2p"
        / "local"
        / "project-replication"
        / "ephemeral-presence.json"
    )
    presence.parent.mkdir(parents=True, exist_ok=True)
    presence.write_text(
        json.dumps(
            {
                "contract": "wavekit-project-presence/v1",
                "state": "preparing_change",
            }
        ),
        encoding="utf-8",
    )
    bundle_path = tmp_path / "replica.p2pbundle"

    ProjectApplicationService(target).canonical_bundle_export(bundle_path)
    decoded = CanonicalBundleCodec().decode_bundle(bundle_path)
    serialized = canonical_json_bytes(
        {
            "manifest": decoded.manifest.to_dict(),
            "entities": [item.to_dict() for item in decoded.snapshot.entities],
            "relations": [item.to_dict() for item in decoded.snapshot.relations],
            "lineage": list(decoded.snapshot.lineage),
            "blobs": [item.to_dict() for item in decoded.snapshot.blobs],
        }
    )

    assert b"project-replication" not in serialized
    assert b"wavekit-project-presence" not in serialized
    assert b"wavekit-project-activity" not in serialized


@pytest.mark.mcp
def test_linked_mcp_reads_preflight_and_mutations_route_without_raw_sync_tools(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _server, target, _command_value, _batch, _receipt, _transport = _durable_scenario(
        tmp_path
    )
    preflights: list[bool] = []
    submitted: list[dict[str, object]] = []

    class Freshness:
        def to_dict(self) -> dict[str, object]:
            return {
                "source": "remote",
                "stale": False,
                "last_applied_revision": 2,
            }

    def before_operation(self: object, *, mutation: bool) -> Freshness:
        preflights.append(mutation)
        return Freshness()

    def submit_command(self: object, **kwargs: object) -> dict[str, object]:
        submitted.append(dict(kwargs))
        return {
            "receipt": {"status": "completed"},
            "freshness": Freshness().to_dict(),
        }

    monkeypatch.setattr(
        ProjectApplicationService,
        "linked_replica_before_operation",
        before_operation,
    )
    monkeypatch.setattr(
        ProjectApplicationService,
        "linked_replica_submit_command",
        submit_command,
    )

    read = call_tool("p2p_project_domain_show", {"root": str(target)})
    mutation = call_tool(
        "p2p_project_domain_set",
        {
            "root": str(target),
            "key": "software",
            "name": "Software",
            "actor": "untrusted-client-value",
            "linked_operation_id": "op_mcp_domain_1",
            "linked_expected_project_revision": 2,
            "linked_entity_preconditions": [],
        },
    )

    assert preflights == [False]
    assert read["linked_replica_freshness"]["last_applied_revision"] == 2
    assert mutation["mutation_performed"] is True
    assert submitted[0]["operation_id"] == "op_mcp_domain_1"
    assert "actor" not in submitted[0]["payload"]
    assert not any(
        marker in name
        for name in TOOL_NAMES
        for marker in ("replication_feed", "replication_cursor", "replication_blob")
    )
