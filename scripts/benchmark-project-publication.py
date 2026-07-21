#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections.abc import Callable
from contextlib import contextmanager
import inspect
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter
import tracemalloc
from types import SimpleNamespace

from p2p_engine.services.project_publication import ProjectPublicationService


class Counters:
    def __init__(self) -> None:
        self.file_reads = 0
        self.yaml_parses = 0
        self.accepted_provider_calls = 0
        self.vertical_provider_calls = 0

    def reset(self) -> None:
        self.file_reads = 0
        self.yaml_parses = 0
        self.accepted_provider_calls = 0
        self.vertical_provider_calls = 0


@contextmanager
def instrument_reads(root: Path, counters: Counters):
    original_read_bytes = Path.read_bytes
    original_read_text = Path.read_text

    def under_root(path: Path) -> bool:
        try:
            path.resolve().relative_to(root.resolve())
        except ValueError:
            return False
        return True

    def read_bytes(path: Path) -> bytes:
        if under_root(path):
            counters.file_reads += 1
        return original_read_bytes(path)

    def read_text(path: Path, *args, **kwargs) -> str:
        if under_root(path):
            counters.file_reads += 1
        return original_read_text(path, *args, **kwargs)

    Path.read_bytes = read_bytes
    Path.read_text = read_text
    restorers: list[tuple[object, str, object]] = []
    for module_name, attribute in (
        ("p2p_engine.services.project_publication", "_read_yaml_mapping"),
        ("p2p_engine.services.project_publication_contracts", "load_yaml_mapping"),
        ("p2p_engine.services.workspace_reads", "load_yaml"),
    ):
        try:
            module = __import__(module_name, fromlist=[attribute])
            original = getattr(module, attribute)
        except (ImportError, AttributeError):
            continue

        def wrapper(*args, __original=original, **kwargs):
            counters.yaml_parses += 1
            return __original(*args, **kwargs)

        setattr(module, attribute, wrapper)
        restorers.append((module, attribute, original))
    try:
        yield
    finally:
        Path.read_bytes = original_read_bytes
        Path.read_text = original_read_text
        for module, attribute, original in restorers:
            setattr(module, attribute, original)


def measured(operation: Callable[[], object], counters: Counters) -> dict[str, object]:
    counters.reset()
    tracemalloc.start()
    started = perf_counter()
    result = operation()
    elapsed = perf_counter() - started
    peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    return {
        "wall_seconds": round(elapsed, 6),
        "peak_memory_bytes": peak,
        "file_reads": counters.file_reads,
        "yaml_parses": counters.yaml_parses,
        "accepted_provider_calls": counters.accepted_provider_calls,
        "vertical_provider_calls": counters.vertical_provider_calls,
        "result_type": type(result).__name__,
    }


def write_fixture(root: Path, proposal_count: int) -> list[dict[str, object]]:
    p2p = root / ".p2p"
    proposals = p2p / "proposals"
    proposals.mkdir(parents=True)
    (p2p / "project.yml").write_text("project:\n  name: Publication Scale\n", encoding="utf-8")
    records = []
    for number in range(1, proposal_count + 1):
        proposal_id = f"PROP-{number:05d}"
        directory = proposals / f"{proposal_id}-scale"
        directory.mkdir()
        directory.joinpath("proposal.md").write_text(
            f"# {proposal_id}\n\nProject evidence {number}.\n",
            encoding="utf-8",
        )
        records.append(
            {
                "proposal_id": proposal_id,
                "title": f"Evidence {number}",
                "status": "accepted",
                "path": directory,
                "source": directory.relative_to(root).as_posix(),
            }
        )
    return records


def run_case(proposal_count: int) -> dict[str, object]:
    with TemporaryDirectory(prefix="p2p-publication-benchmark-") as temporary:
        root = Path(temporary)
        records = write_fixture(root, proposal_count)
        counters = Counters()

        def accepted() -> list[dict[str, object]]:
            counters.accepted_provider_calls += 1
            return records

        def vertical_memory():
            counters.vertical_provider_calls += 1
            return None

        def export():
            target = root / "outputs" / "latest" / "project.md"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                "# Publication Scale\n\n"
                + "\n".join(f"- {item['proposal_id']}" for item in records)
                + "\n",
                encoding="utf-8",
            )
            return SimpleNamespace(archived_path=None)

        kwargs = {
            "root": root,
            "p2p_dir": root / ".p2p",
            "export_visible_project": export,
            "accepted_proposals": accepted,
        }
        if "vertical_project_memory" in inspect.signature(ProjectPublicationService).parameters:
            kwargs["vertical_project_memory"] = vertical_memory
        service = ProjectPublicationService(**kwargs)
        with instrument_reads(root, counters):
            prepare = measured(service.prepare, counters)
            status = measured(service.status, counters)
            if hasattr(service, "list_editions"):
                list_result = measured(service.list_editions, counters)
                second_edition = measured(lambda: service.prepare(language="it"), counters)
            else:
                list_result = {"supported": False}
                second_edition = {"supported": False}

        paths = service.paths()
        evidence_path = getattr(paths, "evidence_index", None)
        evidence_operations = None
        if evidence_path is not None and evidence_path.exists():
            import yaml

            evidence = yaml.safe_load(evidence_path.read_text(encoding="utf-8"))
            evidence_operations = summarize_read_operations(evidence.get("read_operations"))
        packet_path = getattr(paths, "curator_input")
        export_path = getattr(paths, "source_export")
        return {
            "proposal_count": proposal_count,
            "prepare": prepare,
            "status": status,
            "list": list_result,
            "second_edition_prepare": second_edition,
            "export_bytes": export_path.stat().st_size,
            "packet_bytes": packet_path.stat().st_size,
            "evidence_bytes": evidence_path.stat().st_size if evidence_path is not None else 0,
            "evidence_read_operations": evidence_operations,
        }


def summarize_read_operations(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    result: dict[str, object] = {}
    for key, item in value.items():
        if isinstance(item, dict):
            result[key] = {
                "keys": len(item),
                "total": sum(number for number in item.values() if isinstance(number, int)),
            }
        else:
            result[key] = item
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True)
    parser.add_argument("--counts", nargs="+", type=int, default=[100, 1_000, 10_000])
    args = parser.parse_args()
    print(
        json.dumps(
            {
                "label": args.label,
                "source": inspect.getfile(ProjectPublicationService),
                "results": [run_case(count) for count in args.counts],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
