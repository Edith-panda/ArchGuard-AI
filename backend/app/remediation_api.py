from __future__ import annotations

from typing import Any

from .approval_engine import approve_proposal, get_proposal, reject_proposal
from .github_mcp_executor import GitHubMCPError, create_github_remediation_pr, github_mcp_status, preview_github_remediation


def get_remediation_state(proposal_id: str) -> dict[str, Any]:
    proposal = get_proposal(proposal_id)
    if not proposal:
        raise ValueError("Remediation proposal not found.")
    return {
        "proposal_id": proposal_id,
        "approval_status": proposal.get("approval_status", "pending"),
        "approved": bool(proposal.get("approved")),
        "strategy": proposal.get("strategy"),
        "change_scope": proposal.get("change_scope"),
        "recommended_change": proposal.get("recommended_change"),
        "validation_checks": proposal.get("validation_checks", []),
        "mcp_execution": proposal.get("mcp_execution"),
        "mcp": github_mcp_status(),
    }


def approve_remediation_for_ui(proposal_id: str) -> dict[str, Any]:
    proposal = approve_proposal(proposal_id)
    return get_remediation_state(proposal["proposal_id"])


def reject_remediation_for_ui(proposal_id: str) -> dict[str, Any]:
    proposal = reject_proposal(proposal_id)
    return get_remediation_state(proposal["proposal_id"])


def preview_remediation_for_ui(proposal_id: str) -> dict[str, Any]:
    return preview_github_remediation(proposal_id)


def execute_remediation_for_ui(proposal_id: str) -> dict[str, Any]:
    try:
        return create_github_remediation_pr(proposal_id)
    except GitHubMCPError as exc:
        raise ValueError(str(exc)) from exc
