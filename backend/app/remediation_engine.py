from __future__ import annotations

import uuid
from typing import Any


SEVERITY_PRIORITY = {
    "critical": 5,
    "high": 4,
    "medium": 3,
    "low": 2,
    "info": 1,
}


def normalize_text(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip()


def normalize_severity(
    severity: str,
) -> str:
    value = normalize_text(
        severity
    ).lower()

    if value not in SEVERITY_PRIORITY:
        return "medium"

    return value


def build_validation_checks(
    finding: dict[str, Any],
) -> list[str]:

    category = normalize_text(
        finding.get("category")
    ).lower()

    issue = normalize_text(
        finding.get("issue")
    ).lower()

    combined = (
        f"{category} {issue}"
    )

    checks = [
        "Re-run ArchGuard architecture analysis.",
        "Verify the original finding is no longer detected.",
    ]

    if (
        "database" in combined
        or "postgres" in combined
    ):
        checks.extend(
            [
                "Verify database redundancy or failover configuration.",
                "Re-run database failure scenario.",
            ]
        )

    if (
        "dependency" in combined
        or "circuit" in combined
    ):
        checks.extend(
            [
                "Verify timeout and failure-isolation behavior.",
                "Re-run dependency failure scenario.",
            ]
        )

    if (
        "security" in combined
        or "auth" in combined
    ):
        checks.extend(
            [
                "Re-run security analysis.",
                "Verify least-privilege access remains intact.",
            ]
        )

    if (
        "scal" in combined
        or "performance" in combined
        or "traffic" in combined
    ):
        checks.extend(
            [
                "Re-run traffic spike simulation.",
                "Verify the predicted bottleneck has changed or reduced.",
            ]
        )

    return list(
        dict.fromkeys(
            checks
        )
    )


def remediation_strategy(
    finding: dict[str, Any],
) -> dict[str, Any]:

    component = normalize_text(
        finding.get("component")
    )

    category = normalize_text(
        finding.get("category")
    ).lower()

    issue = normalize_text(
        finding.get("issue")
    ).lower()

    existing_recommendation = (
        normalize_text(
            finding.get(
                "recommendation"
            )
        )
    )

    combined = (
        f"{category} {issue}"
    )


    if (
        "database" in combined
        or "postgres" in combined
        or "single point" in combined
    ):
        return {
            "strategy":
                "increase_database_resilience",

            "recommended_change":
                existing_recommendation
                or (
                    "Introduce database redundancy, "
                    "health-aware failover, backups, "
                    "and bounded connection pools."
                ),

            "proposed_actions": [
                "Add a redundant database instance or managed high-availability configuration.",
                "Define automated failover behavior.",
                "Add backup and restore validation.",
                "Protect the database from retry storms and connection exhaustion.",
            ],

            "change_scope":
                component
                or "database layer",
        }


    if (
        "dependency" in combined
        or "circuit breaker" in combined
        or "cascad" in combined
    ):
        return {
            "strategy":
                "isolate_service_dependency",

            "recommended_change":
                existing_recommendation
                or (
                    "Add timeout, retry, circuit-breaker "
                    "and fallback boundaries."
                ),

            "proposed_actions": [
                "Add explicit request timeouts.",
                "Use bounded retries with backoff.",
                "Introduce a circuit breaker.",
                "Add graceful fallback behavior where possible.",
                "Consider asynchronous messaging for non-blocking workflows.",
            ],

            "change_scope":
                component
                or "service dependency",
        }


    if (
        "security" in combined
        or "authentication" in combined
        or "authorization" in combined
        or "secret" in combined
    ):
        return {
            "strategy":
                "strengthen_security_controls",

            "recommended_change":
                existing_recommendation
                or (
                    "Apply least privilege and strengthen "
                    "authentication, authorization and "
                    "secret-management controls."
                ),

            "proposed_actions": [
                "Review service identities and permissions.",
                "Reduce permissions to the minimum required.",
                "Move secrets to an approved secret-management mechanism.",
                "Validate authentication and authorization boundaries.",
            ],

            "change_scope":
                component
                or "security boundary",
        }


    if (
        "performance" in combined
        or "scalability" in combined
        or "bottleneck" in combined
        or "traffic" in combined
    ):
        return {
            "strategy":
                "improve_scalability",

            "recommended_change":
                existing_recommendation
                or (
                    "Introduce horizontal scaling and "
                    "reduce pressure on shared dependencies."
                ),

            "proposed_actions": [
                "Enable horizontal scaling where appropriate.",
                "Introduce caching for repeatable reads.",
                "Use queues to absorb burst traffic.",
                "Load-test the highest-centrality dependency.",
            ],

            "change_scope":
                component
                or "performance path",
        }


    return {
        "strategy":
            "architecture_improvement",

        "recommended_change":
            existing_recommendation
            or (
                "Apply the recommended architectural "
                "change and validate the affected dependency path."
            ),

        "proposed_actions": [
            existing_recommendation
            or "Review and remediate the identified architectural weakness.",
        ],

        "change_scope":
            component
            or "architecture",
    }


def create_remediation_proposal(
    finding: dict[str, Any],
) -> dict[str, Any]:

    strategy = (
        remediation_strategy(
            finding
        )
    )

    severity = (
        normalize_severity(
            finding.get(
                "severity",
                "medium",
            )
        )
    )

    risk_score = finding.get(
        "risk_score",
        0,
    )

    proposal_id = (
        "rem-"
        +
        uuid.uuid4().hex[:10]
    )

    return {
        "proposal_id":
            proposal_id,

        "status":
            "proposed",

        "requires_human_approval":
            True,

        "approved":
            False,

        "execution_allowed":
            False,

        "finding": {
            "issue":
                finding.get(
                    "issue"
                ),

            "component":
                finding.get(
                    "component"
                ),

            "category":
                finding.get(
                    "category"
                ),

            "severity":
                severity,

            "risk_score":
                risk_score,

            "source":
                finding.get(
                    "source"
                ),
        },

        "strategy":
            strategy[
                "strategy"
            ],

        "change_scope":
            strategy[
                "change_scope"
            ],

        "recommended_change":
            strategy[
                "recommended_change"
            ],

        "proposed_actions":
            strategy[
                "proposed_actions"
            ],

        "validation_checks":
            build_validation_checks(
                finding
            ),

        "safety": {
            "automatic_execution":
                False,

            "human_approval_required":
                True,

            "infrastructure_changes":
                "proposal_only",

            "note":
                (
                    "ArchGuard has generated a remediation "
                    "proposal only. No code, infrastructure "
                    "or external system has been modified."
                ),
        },
    }


def build_remediation_plan(
    findings: list[dict[str, Any]],
) -> dict[str, Any]:

    proposals = [
        create_remediation_proposal(
            finding
        )

        for finding
        in findings
    ]

    proposals.sort(
        key=lambda proposal:
            (
                proposal[
                    "finding"
                ].get(
                    "risk_score",
                    0,
                )
            ),
        reverse=True,
    )

    critical_count = sum(
        1
        for proposal
        in proposals
        if proposal[
            "finding"
        ][
            "severity"
        ] == "critical"
    )

    high_count = sum(
        1
        for proposal
        in proposals
        if proposal[
            "finding"
        ][
            "severity"
        ] == "high"
    )

    return {
        "status":
            "success",

        "workflow_stage":
            "recommend",

        "proposal_count":
            len(
                proposals
            ),

        "critical_proposals":
            critical_count,

        "high_proposals":
            high_count,

        "approval_required":
            True,

        "execution_enabled":
            False,

        "proposals":
            proposals,
    }