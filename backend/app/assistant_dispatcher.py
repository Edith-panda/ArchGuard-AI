from typing import Any, Optional

from .conversation_router import EngineeringIntent


class AssistantDispatchError(Exception):
    """Raised when an assistant request cannot be dispatched."""


def dispatch_assistant_request(
    intent: EngineeringIntent,
    prompt: str,
    architecture: Optional[dict] = None,
) -> dict[str, Any]:
    """
    Dispatch a conversational request to the
    appropriate ArchGuard capability.

    This layer does NOT execute external systems,
    infrastructure changes, or MCP tools.
    """

    if intent == EngineeringIntent.REVIEW:
        return dispatch_review(
            prompt=prompt,
            architecture=architecture,
        )

    if intent == EngineeringIntent.SIMULATE:
        return dispatch_simulation(
            prompt=prompt,
            architecture=architecture,
        )

    if intent == EngineeringIntent.MODIFY:
        return dispatch_modification(
            prompt=prompt,
            architecture=architecture,
        )

    if intent == EngineeringIntent.REMEDIATE:
        return dispatch_remediation(
            prompt=prompt,
            architecture=architecture,
        )

    raise AssistantDispatchError(
        f"No specialized dispatcher for intent: "
        f"{intent.value}"
    )


def require_architecture(
    architecture: Optional[dict],
    intent: EngineeringIntent,
) -> dict:
    """
    Ensure an architecture-dependent operation
    has architecture context.
    """

    if not architecture:
        raise AssistantDispatchError(
            f"The '{intent.value}' request needs "
            "architecture context. Upload architecture "
            "artifacts or provide an architecture first."
        )

    services = architecture.get("services", [])

    if not services:
        raise AssistantDispatchError(
            "Architecture context was provided, but "
            "no services/components were detected."
        )

    return architecture


def dispatch_review(
    prompt: str,
    architecture: Optional[dict],
) -> dict:
    architecture = require_architecture(
        architecture,
        EngineeringIntent.REVIEW,
    )

    return {
        "engine": "architecture_review",
        "status": "ready",
        "prompt": prompt,
        "architecture": architecture,
        "pipeline": [
            "graph_engine",
            "risk_engine",
            "well_architected_engine",
        ],
        "message": (
            "Architecture context is available "
            "for deterministic review."
        ),
    }


def dispatch_simulation(
    prompt: str,
    architecture: Optional[dict],
) -> dict:
    architecture = require_architecture(
        architecture,
        EngineeringIntent.SIMULATE,
    )

    scenario = detect_scenario(prompt)

    return {
        "engine": "scenario_lab",
        "status": "ready",
        "scenario": scenario,
        "prompt": prompt,
        "architecture": architecture,
        "pipeline": [
            "graph_engine",
            "scenario_engine",
            "risk_engine",
        ],
        "message": (
            "Architecture and scenario context "
            "are ready for simulation."
        ),
    }


def dispatch_modification(
    prompt: str,
    architecture: Optional[dict],
) -> dict:
    architecture = require_architecture(
        architecture,
        EngineeringIntent.MODIFY,
    )

    return {
        "engine": "architecture_evolution",
        "status": "ready",
        "prompt": prompt,
        "architecture": architecture,
        "pipeline": [
            "requirements_analysis",
            "digital_twin",
            "impact_analysis",
            "architecture_reasoning",
            "risk_precheck",
        ],
        "message": (
            "Existing architecture and new "
            "requirements are ready for impact analysis."
        ),
    }


def dispatch_remediation(
    prompt: str,
    architecture: Optional[dict],
) -> dict:
    architecture = require_architecture(
        architecture,
        EngineeringIntent.REMEDIATE,
    )

    return {
        "engine": "remediation",
        "status": "ready",
        "prompt": prompt,
        "architecture": architecture,
        "pipeline": [
            "risk_engine",
            "remediation_engine",
            "human_approval",
            "sandbox_execution",
            "verification_engine",
        ],
        "safety": {
            "human_approval_required": True,
            "external_execution_allowed": False,
        },
        "message": (
            "Remediation requires analysis and "
            "explicit human approval before execution."
        ),
    }


def detect_scenario(prompt: str) -> str:
    """
    Convert conversational what-if questions into
    Scenario Lab scenario types.
    """

    text = prompt.lower()

    database_terms = [
        "database goes down",
        "database fails",
        "db goes down",
        "db fails",
        "postgres goes down",
        "postgresql goes down",
        "mysql goes down",
    ]

    if any(term in text for term in database_terms):
        return "database_failure"

    traffic_terms = [
        "traffic spike",
        "10x traffic",
        "100x traffic",
        "more traffic",
        "load spike",
    ]

    if any(term in text for term in traffic_terms):
        return "traffic_spike"

    dependency_terms = [
        "dependency fails",
        "dependency failure",
        "external service fails",
        "third party fails",
    ]

    if any(term in text for term in dependency_terms):
        return "dependency_failure"

    return "component_failure"