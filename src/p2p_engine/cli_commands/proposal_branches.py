from __future__ import annotations

from pathlib import Path

import typer

from p2p_engine.cli_shared import console
from p2p_engine.cli_shared import fail
from p2p_engine.cli_shared import workspace as workspace_for
from p2p_engine.storage.filesystem import ProposalMergeConflict


def register_proposal_branch_commands(proposal_app: typer.Typer) -> None:
    @proposal_app.command("branch")
    def proposal_branch(
        proposal_id: str = typer.Argument(..., help="Proposal ID, e.g. PROP-001"),
        actor: str = typer.Option("local", "--actor", help="Person or agent creating the branch"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Create and check out a managed proposal branch."""
        try:
            branch = workspace_for(root).branch_proposal(proposal_id, actor)
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Managed proposal branch created.[/green]")
        print_proposal_branch(branch)

    @proposal_app.command("status")
    def proposal_branch_status(
        proposal_id: str = typer.Argument(..., help="Proposal ID, e.g. PROP-001"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Show managed proposal branch status."""
        try:
            branch = workspace_for(root).show_proposal_branch(proposal_id)
        except ValueError as exc:
            fail(str(exc))
        console.print("Proposal branch status")
        print_proposal_branch(branch)

    @proposal_app.command("publish")
    def proposal_publish(
        proposal_id: str = typer.Argument(..., help="Proposal ID, e.g. PROP-001"),
        remote: str | None = typer.Option(None, "--remote", help="Override configured Git remote"),
        auto_renumber: bool = typer.Option(False, "--auto-renumber", help="Auto-renumber if the proposal ID collides on remote"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Publish a managed proposal branch to the configured remote."""
        try:
            branch = workspace_for(root).publish_proposal_branch(proposal_id, remote, auto_renumber=auto_renumber)
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Managed proposal branch published.[/green]")
        print_proposal_branch(branch)

    @proposal_app.command("request-review")
    def proposal_request_review(
        proposal_id: str = typer.Argument(..., help="Proposal ID, e.g. PROP-001"),
        provider: str | None = typer.Option(None, "--provider", help="Review provider: generic, github, or gitlab"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Record external review handoff metadata for a published proposal branch."""
        try:
            branch = workspace_for(root).request_proposal_branch_review(proposal_id, provider)
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Managed proposal review requested.[/green]")
        print_proposal_branch(branch)
        review = branch.metadata.get("review", {})
        if isinstance(review, dict) and review.get("suggested_next"):
            console.print(f"  suggested_next: {review['suggested_next']}")

    @proposal_app.command("merge")
    def proposal_merge(
        proposal_id: str = typer.Argument(..., help="Proposal ID, e.g. PROP-001"),
        continue_: bool = typer.Option(False, "--continue", help="Continue merge after manual conflict resolution"),
        abort: bool = typer.Option(False, "--abort", help="Abort a conflicted proposal merge"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Merge a managed proposal branch into its base branch locally."""
        if continue_ and abort:
            fail("Use either --continue or --abort, not both.")
        try:
            if continue_:
                merge = workspace_for(root).continue_merge_proposal_branch(proposal_id)
            elif abort:
                branch = workspace_for(root).abort_merge_proposal_branch(proposal_id)
                console.print("[yellow]Managed proposal merge aborted.[/yellow]")
                print_proposal_branch(branch)
                return
            else:
                merge = workspace_for(root).merge_proposal_branch(proposal_id)
        except ValueError as exc:
            fail(str(exc))
        if isinstance(merge, ProposalMergeConflict):
            console.print("[yellow]Managed proposal merge blocked by conflicts.[/yellow]")
            console.print(f"  proposal: {merge.proposal_id}")
            console.print(f"  source_branch: {merge.branch_name}")
            console.print(f"  base: {merge.base_branch}")
            console.print("  conflicts:")
            for path in merge.conflicted_files:
                console.print(f"    {path}")
            console.print(f"  continue: p2p proposal merge --continue {merge.proposal_id}")
            console.print(f"  abort: p2p proposal merge --abort {merge.proposal_id}")
            raise typer.Exit(1)
        console.print("[green]Managed proposal branch merged.[/green]")
        console.print(f"  proposal: {merge.proposal_id}")
        console.print(f"  source_branch: {merge.branch_name}")
        console.print(f"  base: {merge.base_branch}")
        console.print(f"  merge_commit: {merge.merge_commit}")
        console.print(f"  path: {merge.path}")

    @proposal_app.command("accept-branch")
    def proposal_accept_branch(
        proposal_id: str = typer.Argument(..., help="Proposal ID, e.g. PROP-001"),
        reason: str = typer.Option(..., "--reason", help="Governance reason for accepting the branch"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Record an owner-controlled governance acceptance for a proposal branch."""
        try:
            branch = workspace_for(root).accept_proposal_branch(proposal_id, reason)
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Managed proposal branch accepted.[/green]")
        print_proposal_branch(branch)

    @proposal_app.command("reject-branch")
    def proposal_reject_branch(
        proposal_id: str = typer.Argument(..., help="Proposal ID, e.g. PROP-001"),
        reason: str = typer.Option(..., "--reason", help="Governance reason for rejecting the branch"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Record an owner-controlled governance rejection for a proposal branch."""
        try:
            branch = workspace_for(root).reject_proposal_branch(proposal_id, reason)
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Managed proposal branch rejected.[/green]")
        print_proposal_branch(branch)

    @proposal_app.command("finalize")
    def proposal_finalize(
        proposal_id: str = typer.Argument(..., help="Proposal ID, e.g. PROP-001"),
        remote: str | None = typer.Option(None, "--remote", help="Override configured Git remote"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Finalize a merged proposal branch by pushing its base branch."""
        try:
            finalize = workspace_for(root).finalize_proposal_branch(proposal_id, remote)
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Managed proposal branch finalized.[/green]")
        console.print(f"  proposal: {finalize.proposal_id}")
        console.print(f"  source_branch: {finalize.branch_name}")
        console.print(f"  base: {finalize.base_branch}")
        console.print(f"  remote: {finalize.remote}")
        console.print(f"  remote_url: {finalize.remote_url}")
        console.print(f"  finalize_commit: {finalize.finalize_commit}")
        console.print(f"  path: {finalize.path}")
        console.print("  cleanup: disabled")

    @proposal_app.command("cleanup")
    def proposal_cleanup(
        proposal_id: str = typer.Argument(..., help="Proposal ID, e.g. PROP-001"),
        delete_remote: bool = typer.Option(False, "--delete-remote", help="Also delete the remote managed proposal branch"),
        remote: str | None = typer.Option(None, "--remote", help="Override configured Git remote"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Delete a finalized, rejected, or retired managed proposal branch."""
        try:
            cleanup = workspace_for(root).cleanup_proposal_branch(proposal_id, delete_remote=delete_remote, remote=remote)
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Managed proposal branch cleaned.[/green]")
        console.print(f"  proposal: {cleanup.proposal_id}")
        console.print(f"  source_branch: {cleanup.branch_name}")
        console.print(f"  base: {cleanup.base_branch}")
        console.print(f"  remote: {cleanup.remote}")
        console.print(f"  remote_url: {cleanup.remote_url or 'none'}")
        console.print(f"  cleanup_commit: {cleanup.cleanup_commit}")
        console.print(f"  local_deleted: {str(cleanup.local_deleted).lower()}")
        console.print(f"  remote_deleted: {str(cleanup.remote_deleted).lower()}")
        console.print(f"  path: {cleanup.path}")

    @proposal_app.command("retire-branch")
    def proposal_retire_branch(
        proposal_id: str = typer.Argument(..., help="Proposal ID, e.g. PROP-001"),
        reason: str = typer.Option(..., "--reason", help="Retirement reason"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Retire a managed proposal branch without merging it."""
        try:
            branch = workspace_for(root).retire_proposal_branch(proposal_id, reason)
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Managed proposal branch retired.[/green]")
        print_proposal_branch(branch)

    @proposal_app.command("scan")
    def proposal_scan(root: Path = typer.Option(Path.cwd(), "--root", help="Project root")) -> None:
        """Scan local P2P-managed proposal branches without checkout."""
        try:
            scan = workspace_for(root).scan_proposal_branches()
        except ValueError as exc:
            fail(str(exc))
        console.print("Proposal branch scan")
        console.print(f"  scanned_branches: {len(scan.scanned_branches)}")
        console.print(f"  proposal_branches: {len(scan.proposals)}")
        console.print(f"  registry: {scan.path}")
        for item in scan.proposals:
            console.print(
                f"  {item.get('proposal_id')}  {item.get('status')}  {item.get('branch_name')}  {item.get('actor')}"
            )


def print_proposal_branch(branch: object) -> None:
    console.print(f"  proposal: {getattr(branch, 'proposal_id')}")
    console.print(f"  status: {getattr(branch, 'status')}")
    console.print(f"  branch: {getattr(branch, 'branch_name') or 'none'}")
    console.print(f"  base_branch: {getattr(branch, 'base_branch') or 'none'}")
    console.print(f"  actor: {getattr(branch, 'actor') or 'none'}")
    console.print(f"  hash16: {getattr(branch, 'branch_hash16') or 'none'}")
    console.print(f"  remote: {getattr(branch, 'remote') or 'none'}")
    console.print(f"  remote_url: {getattr(branch, 'remote_url') or 'none'}")
    console.print(f"  path: {getattr(branch, 'path')}")
