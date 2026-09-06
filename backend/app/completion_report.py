from __future__ import annotations

from typing import Any

from .architecture_versions import compare_architectures
from .verification_engine import verify_remediation


def build_completion_report(
    before_architecture: dict[str, Any],
    after_architecture: dict[str, Any],
    before_findings: list[dict[str, Any]],
    after_findings: list[dict[str, Any]],
    before_health: dict[str, Any] | None = None,
    after_health: dict[str, Any] | None = None,
    mcp_execution: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the final ArchGuard outcome used at the end of a remediation loop."""
    architecture_delta = compare_architectures(before_architecture, after_architecture)
    verification = verify_remediation(
        before_findings=before_findings,
        after_findings=after_findings,
        before_well_architected=before_health or {},
        after_well_architected=after_health or {},
    )
    execution = mcp_execution or {}

    return {
        "workflow": "design_understand_review_simulate_evolve_remediate_verify",
        "status": verification.get("status", "unknown"),
        "improved": bool(verification.get("improved")),
        "architecture_delta": architecture_delta,
        "risk": {
            "before_high_or_critical": verification.get("before", {}).get("high_or_critical", 0),
            "after_high_or_critical": verification.get("after", {}).get("high_or_critical", 0),
            "risk_reduction": verification.get("risk_reduction", 0),
        },
        "architecture_health": verification.get("well_architected", {}),
        "external_action": {
            "provider": execution.get("provider"),
            "action": execution.get("action"),
            "pull_request_url": execution.get("pull_request_url"),
            "completed": bool(execution.get("completed")),
            "production_modified": bool(execution.get("production_modified", False)),
        },
        "human_review_still_required": True,
        "done_when": (
            "The changed architecture has been re-ingested, verification reports the expected improvement, "
            "and a human has reviewed the external change."
        ),
    }
