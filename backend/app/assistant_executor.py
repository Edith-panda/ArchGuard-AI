from typing import Any, Optional

from .conversation_router import EngineeringIntent

from .graph_engine import build_graph
from .risk_engine import analyze_risks
from .well_architected import score_well_architected
from .scenario_lab import run_scenario


class AssistantExecutionError(Exception):
    pass


def _normalize_findings(findings: list[Any]) -> list[dict]:
    """
    Convert Pydantic models / dict findings
    into plain dictionaries.
    """

    normalized = []

    for finding in findings or []:

        if isinstance(finding, dict):
            normalized.append(finding)

        elif hasattr(finding, "model_dump"):
            normalized.append(
                finding.model_dump()
            )

        elif hasattr(finding, "dict"):
            normalized.append(
                finding.dict()
            )

    return normalized


def require_architecture(
    architecture: Optional[dict],
) -> dict:

    if not architecture:
        raise AssistantExecutionError(
            "Architecture is required for "
            "this operation."
        )

    services = architecture.get(
        "services",
        []
    )

    if not services:
        raise AssistantExecutionError(
            "No architecture components "
            "were detected."
        )

    return architecture


def detect_scenario(
    prompt: str,
) -> dict:
    """
    Convert a natural-language scenario
    into Scenario Lab parameters.
    """

    text = prompt.lower()

    if any(
        term in text
        for term in [
            "database fails",
            "database goes down",
            "db fails",
            "db goes down",
            "postgres fails",
            "postgres goes down",
        ]
    ):
        return {
            "scenario_type":
                "database_failure",
        }

    if any(
        term in text
        for term in [
            "10x traffic",
            "100x traffic",
            "traffic spike",
            "load spike",
            "more traffic",
        ]
    ):
        return {
            "scenario_type":
                "traffic_spike",
        }

    if any(
        term in text
        for term in [
            "dependency fails",
            "dependency failure",
            "third party fails",
            "external service fails",
        ]
    ):
        return {
            "scenario_type":
                "dependency_failure",
        }

    return {
        "scenario_type":
            "component_failure",
    }


def execute_review(
    architecture: dict,
) -> dict:

    architecture = require_architecture(
        architecture
    )

    graph = build_graph(
        architecture
    )

    findings = analyze_risks(
        architecture,
        graph,
    )

    normalized_findings = (
        _normalize_findings(
            findings
        )
    )

    waf = score_well_architected(
        normalized_findings
    )

    return {
        "engine":
            "architecture_review",

        "graph": {
            "nodes":
                graph.number_of_nodes(),

            "edges":
                graph.number_of_edges(),
        },

        "findings":
            normalized_findings,

        "well_architected":
            waf,
    }


def execute_simulation(
    prompt: str,
    architecture: dict,
) -> dict:

    architecture = require_architecture(
        architecture
    )

    scenario = detect_scenario(
        prompt
    )

    result = run_scenario(
        architecture=architecture,
        scenario_type=(
            scenario[
                "scenario_type"
            ]
        ),
    )

    return {
        "engine":
            "scenario_lab",

        "scenario":
            scenario,

        "result":
            result,
    }


def execute_assistant_intent(
    intent: EngineeringIntent,
    prompt: str,
    architecture: Optional[dict],
) -> dict:
    """
    Execute local ArchGuard engines based
    on detected engineering intent.
    """

    if intent == EngineeringIntent.REVIEW:

        return execute_review(
            architecture
        )

    if intent == EngineeringIntent.SIMULATE:

        return execute_simulation(
            prompt,
            architecture,
        )

    if intent == EngineeringIntent.MODIFY:

        return {
            "engine":
                "architecture_evolution",

            "status":
                "not_implemented",

            "message": (
                "Architecture impact analysis "
                "will be implemented next."
            ),
        }

    if intent == EngineeringIntent.DESIGN:

        return {
            "engine":
                "system_design",

            "status":
                "requires_reasoning",

            "message": (
                "System-design generation "
                "requires the reasoning layer."
            ),
        }

    if intent == EngineeringIntent.QUESTION:

        return {
            "engine":
                "architecture_qa",

            "status":
                "requires_reasoning",
        }

    if intent == EngineeringIntent.REMEDIATE:

        return {
            "engine":
                "remediation",

            "status":
                "approval_required",

            "external_execution":
                False,
        }

    raise AssistantExecutionError(
        f"Unsupported intent: {intent}"
    )