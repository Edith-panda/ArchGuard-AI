from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from .approval_engine import get_proposal
from .architecture_versions import compare_architectures
from .github_mcp_executor import (
    create_github_remediation_pr,
    github_mcp_status,
    preview_github_remediation,
)
from .verification_engine import verify_remediation


mcp = FastMCP("ArchGuard Engineering Tools")


@mcp.tool()
def archguard_mcp_status() -> dict[str, Any]:
    """Return MCP/GitHub integration status without exposing secrets."""
    return github_mcp_status()


@mcp.tool()
def inspect_remediation(proposal_id: str) -> dict[str, Any]:
    """Inspect a remediation proposal and its approval state. Read-only."""
    proposal = get_proposal(proposal_id)
    if not proposal:
        return {"status": "not_found", "proposal_id": proposal_id}
    return {
        "status": "success",
        "proposal_id": proposal_id,
        "approval_status": proposal.get("approval_status"),
        "approved": bool(proposal.get("approved")),
        "strategy": proposal.get("strategy"),
        "change_scope": proposal.get("change_scope"),
        "recommended_change": proposal.get("recommended_change"),
        "validation_checks": proposal.get("validation_checks", []),
        "mcp_execution": proposal.get("mcp_execution"),
    }


@mcp.tool()
def preview_remediation_pull_request(proposal_id: str) -> dict[str, Any]:
    """Preview the exact GitHub PR artifact ArchGuard would create. No write occurs."""
    return preview_github_remediation(proposal_id)


@mcp.tool()
def create_approved_remediation_pull_request(
    proposal_id: str,
    title: str = "",
) -> dict[str, Any]:
    """Create a GitHub PR only for an already human-approved ArchGuard proposal.

    This tool never deploys infrastructure and never pushes to the default branch.
    Repository writes also require ARCHGUARD_GITHUB_WRITE_ENABLED=true.
    """
    return create_github_remediation_pr(proposal_id, title=title or None)


@mcp.tool()
def compare_architecture_versions(
    before_architecture: dict[str, Any],
    after_architecture: dict[str, Any],
) -> dict[str, Any]:
    """Return an explicit V1-to-V2 component and dependency delta."""
    return compare_architectures(before_architecture, after_architecture)


@mcp.tool()
def verify_before_after(
    before_findings: list[dict[str, Any]],
    after_findings: list[dict[str, Any]],
    before_health: dict[str, Any] | None = None,
    after_health: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compare before/after risks after a reviewed remediation has been applied."""
    return verify_remediation(
        before_findings=before_findings,
        after_findings=after_findings,
        before_well_architected=before_health or {},
        after_well_architected=after_health or {},
    )


if __name__ == "__main__":
    mcp.run()
