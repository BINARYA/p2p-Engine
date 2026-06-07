from __future__ import annotations

from pathlib import Path

import typer

from p2p_engine.cli_shared import console
from p2p_engine.cli_shared import fail
from p2p_engine.cli_shared import workspace as workspace_for
from p2p_engine.cli_shared import yaml_dump_for_cli
from p2p_engine.storage.filesystem import WorkAcceptConflict


def register_work_commands(work_app: typer.Typer) -> None:
    @work_app.command("plan")
    def work_plan(
        change: str = typer.Option(..., "--change", help="Change Set ID, e.g. CHANGE-001"),
        target: str = typer.Option(..., "--target", help="Validated export target: generic, openspec, or speckit"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Create a P2P Work handoff manifest without creating Git branches or commits."""
        try:
            work = workspace_for(root).create_work_plan(change, target)
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Work plan created.[/green]")
        console.print(f"  work: {work.work_id}")
        console.print(f"  status: {work.status}")
        console.print(f"  change: {work.change_id}")
        console.print(f"  target: {work.target}")
        console.print(f"  branch: {work.branch_name}")
        console.print(f"  path: {work.path}")

    @work_app.command("list")
    def work_list(root: Path = typer.Option(Path.cwd(), "--root", help="Project root")) -> None:
        """List P2P Work manifests."""
        works = workspace_for(root).work_statuses()
        console.print("Work items")
        if not works:
            console.print("  none")
            return
        for work in works:
            console.print(f"  {work.work_id}  {work.status}  {work.change_id}  {work.target}")

    @work_app.command("status")
    def work_status(root: Path = typer.Option(Path.cwd(), "--root", help="Project root")) -> None:
        """Show an operational read-only summary of P2P Work items."""
        works = workspace_for(root).work_summaries()
        console.print("Work status")
        if not works:
            console.print("  none")
            return
        for work in works:
            console.print(f"{work.work_id}  {work.status}")
            console.print(f"  change: {work.change_id}")
            console.print(f"  target: {work.target}")
            console.print(f"  branch: {work.branch_name or 'none'}")
            console.print(f"  base: {work.base_branch}")
            if work.remote:
                console.print(f"  remote: {work.remote}")
            console.print(f"  next: {work.next_action}")
            console.print(f"  note: {work.note}")

    @work_app.command("scan")
    def work_scan(root: Path = typer.Option(Path.cwd(), "--root", help="Project root")) -> None:
        """Scan local P2P-managed work branches without checkout."""
        scan = workspace_for(root).scan_work_branches()
        console.print("Work branch scan")
        console.print(f"  branches: {len(scan.scanned_branches)}")
        console.print(f"  work_items: {len(scan.work_items)}")
        console.print(f"  registry: {scan.path}")
        for item in scan.work_items:
            console.print(
                f"  {item.get('work_id')}  {item.get('status')}  {item.get('change')}  "
                f"{item.get('target')}  {item.get('branch')}"
            )

    @work_app.command("branch")
    def work_branch(
        work_id: str = typer.Argument(..., help="Work ID, e.g. WORK-001"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Create and switch to the P2P-managed branch for a planned Work item."""
        try:
            branch = workspace_for(root).branch_work(work_id)
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Managed work branch created.[/green]")
        console.print(f"  work: {branch.work_id}")
        console.print(f"  branch: {branch.branch_name}")
        console.print(f"  base: {branch.base_branch}")
        console.print(f"  base_commit: {branch.base_commit}")
        console.print(f"  path: {branch.path}")
        console.print("  commits: disabled")
        console.print("  merge: owner-controlled")

    @work_app.command("retire")
    def work_retire(
        work_id: str = typer.Argument(..., help="Work ID, e.g. WORK-001"),
        reason: str = typer.Option(..., "--reason", help="Why this planned Work item is obsolete"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Retire an obsolete planned Work manifest without touching Git branches."""
        try:
            retired = workspace_for(root).retire_work(work_id, reason)
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Managed work retired.[/green]")
        console.print(f"  work: {retired.work_id}")
        console.print(f"  status: {retired.status}")
        console.print(f"  reason: {retired.reason}")
        console.print(f"  path: {retired.path}")
        console.print("  git: unchanged")

    @work_app.command("submit")
    def work_submit(
        work_id: str = typer.Argument(..., help="Work ID, e.g. WORK-001"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Create a local managed submit commit for a branched Work item."""
        try:
            submit = workspace_for(root).submit_work(work_id)
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Managed work submitted.[/green]")
        console.print(f"  work: {submit.work_id}")
        console.print(f"  branch: {submit.branch_name}")
        console.print(f"  commit: {submit.commit}")
        console.print(f"  changed_files: {len(submit.changed_files)}")
        for path in submit.changed_files:
            console.print(f"    {path}")
        console.print("  push: disabled")
        console.print("  merge: owner-controlled")

    @work_app.command("review")
    def work_review(
        work_id: str = typer.Argument(..., help="Work ID, e.g. WORK-001"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Request local owner review for a submitted Work item."""
        try:
            review = workspace_for(root).review_work(work_id)
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Managed work review requested.[/green]")
        console.print(f"  work: {review.work_id}")
        console.print(f"  branch: {review.branch_name}")
        console.print(f"  review_commit: {review.review_commit}")
        console.print(f"  metadata_commit: {review.metadata_commit}")
        console.print("  push: disabled")
        console.print("  pull_request: disabled")
        console.print("  merge: owner-controlled")

    @work_app.command("publish")
    def work_publish(
        work_id: str = typer.Argument(..., help="Work ID, e.g. WORK-001"),
        remote: str = typer.Option("origin", "--remote", help="Git remote to publish the managed branch to"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Publish a reviewed managed Work branch to a remote without opening a PR or merging."""
        try:
            publish = workspace_for(root).publish_work(work_id, remote)
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Managed work published.[/green]")
        console.print(f"  work: {publish.work_id}")
        console.print(f"  branch: {publish.branch_name}")
        console.print(f"  remote: {publish.remote}")
        console.print(f"  remote_url: {publish.remote_url}")
        console.print(f"  publish_commit: {publish.publish_commit}")
        console.print("  pull_request: disabled")
        console.print("  merge: owner-controlled")

    @work_app.command("request-review")
    def work_request_review(
        work_id: str = typer.Argument(..., help="Work ID, e.g. WORK-001"),
        provider: str | None = typer.Option(None, "--provider", help="External provider: generic, github, or gitlab"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Record provider-agnostic external review handoff for a published Work item."""
        try:
            review = workspace_for(root).request_external_work_review(work_id, provider)
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]External review request recorded.[/green]")
        console.print(f"  work: {review.work_id}")
        console.print(f"  branch: {review.branch_name}")
        console.print(f"  provider: {review.provider}")
        console.print(f"  remote: {review.remote}")
        console.print(f"  remote_url: {review.remote_url}")
        console.print(f"  metadata_commit: {review.metadata_commit}")
        console.print("  opens_external_request: false")
        console.print("  merge: owner-controlled")
        console.print(f"  suggested_next: {review.suggested_next}")

    @work_app.command("accept")
    def work_accept(
        work_id: str = typer.Argument(..., help="Work ID, e.g. WORK-001"),
        continue_: bool = typer.Option(False, "--continue", help="Continue accept after manual conflict resolution"),
        abort: bool = typer.Option(False, "--abort", help="Abort a conflicted accept merge"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Accept a published Work item by merging its managed branch into the base branch locally."""
        if continue_ and abort:
            fail("Use either --continue or --abort, not both.")
        try:
            if continue_:
                accept = workspace_for(root).continue_accept_work(work_id)
            elif abort:
                work = workspace_for(root).abort_accept_work(work_id)
                console.print("[yellow]Managed work accept aborted.[/yellow]")
                console.print(f"  work: {work.work_id}")
                console.print(f"  status: {work.status}")
                console.print(f"  branch: {work.branch_name}")
                return
            else:
                accept = workspace_for(root).accept_work(work_id)
        except ValueError as exc:
            fail(str(exc))
        if isinstance(accept, WorkAcceptConflict):
            console.print("[yellow]Managed work accept blocked by merge conflicts.[/yellow]")
            console.print(f"  work: {accept.work_id}")
            console.print(f"  source_branch: {accept.branch_name}")
            console.print(f"  base: {accept.base_branch}")
            console.print("  conflicts:")
            for path in accept.conflicted_files:
                console.print(f"    {path}")
            console.print(f"  continue: p2p work accept --continue {accept.work_id}")
            console.print(f"  abort: p2p work accept --abort {accept.work_id}")
            raise typer.Exit(1)
        console.print("[green]Managed work accepted.[/green]")
        console.print(f"  work: {accept.work_id}")
        console.print(f"  source_branch: {accept.branch_name}")
        console.print(f"  merged_into: {accept.base_branch}")
        console.print(f"  merge_commit: {accept.merge_commit}")
        console.print("  push: disabled")
        console.print("  cleanup: disabled")

    @work_app.command("finalize")
    def work_finalize(
        work_id: str = typer.Argument(..., help="Work ID, e.g. WORK-001"),
        remote: str = typer.Option("origin", "--remote", help="Git remote to push the base branch to"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Finalize an accepted Work item by pushing the base branch to a remote."""
        try:
            finalize = workspace_for(root).finalize_work(work_id, remote)
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Managed work finalized.[/green]")
        console.print(f"  work: {finalize.work_id}")
        console.print(f"  base_branch: {finalize.base_branch}")
        console.print(f"  remote: {finalize.remote}")
        console.print(f"  remote_url: {finalize.remote_url}")
        console.print(f"  finalize_commit: {finalize.finalize_commit}")
        console.print("  cleanup: disabled")

    @work_app.command("cleanup")
    def work_cleanup(
        work_id: str = typer.Argument(..., help="Work ID, e.g. WORK-001"),
        delete_remote: bool = typer.Option(False, "--remote", help="Also delete the remote managed Work branch"),
        remote: str = typer.Option("origin", "--remote-name", help="Git remote used for cleanup metadata and optional branch deletion"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Clean up finalized managed Work branches."""
        try:
            cleanup = workspace_for(root).cleanup_work(work_id, delete_remote=delete_remote, remote=remote)
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Managed work cleaned.[/green]")
        console.print(f"  work: {cleanup.work_id}")
        console.print(f"  branch: {cleanup.branch_name}")
        console.print(f"  base_branch: {cleanup.base_branch}")
        console.print(f"  remote: {cleanup.remote}")
        console.print(f"  cleanup_commit: {cleanup.cleanup_commit}")
        console.print(f"  local_deleted: {str(cleanup.local_deleted).lower()}")
        console.print(f"  remote_deleted: {str(cleanup.remote_deleted).lower()}")

    @work_app.command("show")
    def work_show(
        work_id: str = typer.Argument(..., help="Work ID, e.g. WORK-001"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Show a P2P Work manifest."""
        try:
            work = workspace_for(root).show_work(work_id)
        except ValueError as exc:
            fail(str(exc))
        console.print(f"{work.work_id} - {work.status}")
        console.print(f"  change: {work.change_id}")
        console.print(f"  target: {work.target}")
        console.print(f"  branch: {work.branch_name}")
        console.print(f"  path: {work.path}")
        console.print(yaml_dump_for_cli(work.manifest))
