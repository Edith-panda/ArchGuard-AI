import re
from typing import Any, Optional

from .analyzer import analyze_architecture
from .conversation_router import EngineeringIntent
from .graph_engine import build_architecture_graph
from .risk_engine import assign_risk_scores
from .well_architected import score_well_architected
from .scenario_lab import run_scenario


class AssistantExecutionError(Exception):
    pass


def _normalize_findings(findings: list[Any]) -> list[dict]:
    normalized = []
    for finding in findings or []:
        if isinstance(finding, dict):
            normalized.append(finding)
        elif hasattr(finding, "model_dump"):
            normalized.append(finding.model_dump())
        elif hasattr(finding, "dict"):
            normalized.append(finding.dict())
    return normalized


def require_architecture(architecture: Optional[dict]) -> dict:
    if not architecture:
        raise AssistantExecutionError("Architecture is required for this operation.")
    if not architecture.get("services"):
        raise AssistantExecutionError("No architecture components were detected.")
    return architecture


def _find_database(architecture: dict) -> Optional[str]:
    for service in architecture.get("services", []):
        service_type = str(service.get("type", "")).lower()
        name = str(service.get("name", ""))
        if service_type == "database" or any(
            term in name.lower()
            for term in ("postgres", "mysql", "mongo", "database", " db")
        ):
            return name
    return None


def _find_named_component(prompt: str, architecture: dict) -> Optional[str]:
    text = prompt.lower()
    candidates = sorted(
        (str(s.get("name", "")) for s in architecture.get("services", [])),
        key=len,
        reverse=True,
    )
    return next((name for name in candidates if name and name.lower() in text), None)


def detect_scenario(prompt: str, architecture: dict) -> dict:
    text = prompt.lower()

    if any(term in text for term in (
        "database fails", "database goes down", "db fails", "db goes down",
        "postgres fails", "postgres goes down",
    )):
        return {
            "scenario_type": "database_failure",
            "target": _find_named_component(prompt, architecture) or _find_database(architecture),
            "traffic_multiplier": 1.0,
        }

    if any(term in text for term in (
        "traffic spike", "load spike", "more traffic", "10x traffic", "100x traffic",
    )):
        match = re.search(r"(\d+(?:\.\d+)?)\s*[x×]", text)
        multiplier = float(match.group(1)) if match else 10.0
        return {
            "scenario_type": "traffic_spike",
            "target": None,
            "traffic_multiplier": multiplier,
        }

    if any(term in text for term in (
        "dependency fails", "dependency failure", "third party fails",
        "external service fails",
    )):
        return {
            "scenario_type": "dependency_failure",
            "target": _find_named_component(prompt, architecture),
            "traffic_multiplier": 1.0,
        }

    return {
        "scenario_type": "component_failure",
        "target": _find_named_component(prompt, architecture),
        "traffic_multiplier": 1.0,
    }


def execute_review(architecture: dict) -> dict:
    architecture = require_architecture(architecture)
    graph = build_architecture_graph(architecture)
    findings = assign_risk_scores(analyze_architecture(architecture))
    normalized_findings = _normalize_findings(findings)
    waf = score_well_architected(normalized_findings)

    return {
        "engine": "architecture_review",
        "graph": {
            "nodes": graph.number_of_nodes(),
            "edges": graph.number_of_edges(),
        },
        "findings": normalized_findings,
        "well_architected": waf,
    }


def execute_simulation(prompt: str, architecture: dict) -> dict:
    architecture = require_architecture(architecture)
    graph = build_architecture_graph(architecture)
    scenario = detect_scenario(prompt, architecture)

    result = run_scenario(
        graph=graph,
        scenario_type=scenario["scenario_type"],
        target=scenario.get("target"),
        traffic_multiplier=scenario.get("traffic_multiplier", 1.0),
    )

    return {
        "engine": "scenario_lab",
        "scenario": scenario,
        "result": result,
    }


def execute_assistant_intent(
    intent: EngineeringIntent,
    prompt: str,
    architecture: Optional[dict],
) -> dict:
    if intent == EngineeringIntent.REVIEW:
        return execute_review(architecture)

    if intent == EngineeringIntent.SIMULATE:
        return execute_simulation(prompt, architecture)

    if intent == EngineeringIntent.MODIFY:
        return {
            "engine": "architecture_evolution",
            "status": "requires_reasoning",
            "message": "Architecture impact analysis requires the reasoning layer.",
        }

    if intent == EngineeringIntent.DESIGN:
        return {
            "engine": "system_design",
            "status": "requires_reasoning",
            "message": "System-design generation requires the reasoning layer.",
        }

    if intent == EngineeringIntent.QUESTION:
        return {"engine": "architecture_qa", "status": "requires_reasoning"}

    if intent == EngineeringIntent.REMEDIATE:
        return {
            "engine": "remediation",
            "status": "approval_required",
            "external_execution": False,
        }

    raise AssistantExecutionError(f"Unsupported intent: {intent}")
