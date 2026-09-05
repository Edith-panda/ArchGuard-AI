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


def _infer_component_type(name: str) -> str:
    lower = name.lower()
    if any(token in lower for token in ("postgres", "mysql", "database", " db")):
        return "database"
    if any(token in lower for token in ("kafka", "queue", "topic", "pubsub")):
        return "queue"
    if "gateway" in lower:
        return "gateway"
    if "client" in lower:
        return "client"
    return "microservice"


def _clean_component_name(value: str) -> str:
    value = value.strip(" .,:;()[]{}\n\t")
    value = re.sub(r"^(?:one|the|a|an)\s+", "", value, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", value).strip()


def _looks_like_component(value: str) -> bool:
    lower = value.lower()
    return bool(
        lower in {"postgresql", "postgres", "kafka", "redis"}
        or any(token in lower for token in (" service", " client", " gateway", " database", " db"))
    )


def _architecture_from_prompt(prompt: str) -> Optional[dict]:
    """Conservatively derive an architecture graph from explicit prose in the prompt.

    This is intentionally deterministic and only recognizes relationships the user
    directly states (arrow chains, explicit calls, shared databases, Kafka consumers).
    It is a fallback for conversational SIMULATE requests when no file/manual artifact
    produced a canonical architecture.
    """
    services: dict[str, dict] = {}
    connections: set[tuple[str, str]] = set()

    def add_service(name: str):
        cleaned = _clean_component_name(name)
        if not cleaned or not _looks_like_component(cleaned):
            return None
        key = cleaned.lower()
        if key not in services:
            services[key] = {
                "name": cleaned,
                "type": _infer_component_type(cleaned),
                "evidence": [{
                    "filename": "conversation-prompt",
                    "reason": "Explicitly described in the user prompt",
                }],
            }
        return services[key]["name"]

    def add_connection(source: str, target: str):
        src = add_service(source)
        dst = add_service(target)
        if src and dst and src != dst:
            connections.add((src, dst))

    # Explicit flow chains: Web Client → API Gateway → Order Service → Payment Service
    for sentence in re.split(r"[\n.!?]", prompt):
        if "→" in sentence or "->" in sentence:
            parts = re.split(r"\s*(?:→|->)\s*", sentence)
            parts = [_clean_component_name(part) for part in parts]
            component_parts = [part for part in parts if _looks_like_component(part)]
            for source, target in zip(component_parts, component_parts[1:]):
                add_connection(source, target)

    # Named service/gateway/client/database mentions become nodes.
    component_pattern = re.compile(
        r"\b([A-Z][A-Za-z0-9-]*(?:\s+[A-Z][A-Za-z0-9-]*)*\s+"
        r"(?:Service|Client|Gateway|Database|DB))\b"
    )
    for match in component_pattern.finditer(prompt):
        add_service(match.group(1))

    if re.search(r"\bPostgreSQL\b", prompt, re.IGNORECASE):
        add_service("PostgreSQL")
    if re.search(r"\bKafka\b", prompt, re.IGNORECASE):
        add_service("Kafka")

    # Explicit synchronous calls: Order Service synchronously calls Inventory Service and Payment Service.
    call_pattern = re.compile(
        r"([A-Z][A-Za-z0-9-]*(?:\s+[A-Z][A-Za-z0-9-]*)*\s+Service)\s+"
        r"(?:synchronously\s+)?calls\s+([^.!?]+)",
        re.IGNORECASE,
    )
    for match in call_pattern.finditer(prompt):
        source = match.group(1)
        targets = component_pattern.findall(match.group(2))
        for target in targets:
            add_connection(source, target)

    # Explicit shared PostgreSQL dependency.
    shared_db_pattern = re.compile(
        r"([^.!?]+?)\s+share(?:s)?\s+(?:one\s+|a\s+|the\s+)?PostgreSQL\s+database",
        re.IGNORECASE,
    )
    for match in shared_db_pattern.finditer(prompt):
        database_name = add_service("PostgreSQL")
        if database_name:
            for service_name in component_pattern.findall(match.group(1)):
                add_connection(service_name, database_name)

    # Explicit Kafka consumption: Notification Service consumes ... from Kafka.
    kafka_consumer_pattern = re.compile(
        r"([A-Z][A-Za-z0-9-]*(?:\s+[A-Z][A-Za-z0-9-]*)*\s+Service)\s+"
        r"consumes?[^.!?]*\sfrom\s+Kafka",
        re.IGNORECASE,
    )
    for match in kafka_consumer_pattern.finditer(prompt):
        add_connection("Kafka", match.group(1))

    if not services:
        return None

    return {
        "services": list(services.values()),
        "connections": [[source, target] for source, target in sorted(connections)],
        "connection_evidence": [],
        "assumptions": [
            "Architecture was reconstructed conservatively from explicit relationships in the conversational prompt."
        ],
    }


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
        "database fails", "database goes down", "database outage",
        "db fails", "db goes down", "db outage",
        "postgres fails", "postgres goes down", "postgres outage",
        "postgresql fails", "postgresql goes down", "postgresql outage",
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


def execute_simulation(prompt: str, architecture: Optional[dict]) -> dict:
    architecture_source = "ingested_artifacts"
    if not architecture or not architecture.get("services"):
        architecture = _architecture_from_prompt(prompt)
        architecture_source = "conversation_prompt"

    architecture = require_architecture(architecture)
    graph = build_architecture_graph(architecture)
    scenario = detect_scenario(prompt, architecture)

    result = run_scenario(
        graph=graph,
        scenario_type=scenario["scenario_type"],
        target=scenario.get("target"),
        traffic_multiplier=scenario.get("traffic_multiplier", 1.0),
    )

    # Include deterministic review context as well so compound prompts such as
    # "review + simulate + propose migration" still have grounded risk data.
    findings = assign_risk_scores(analyze_architecture(architecture))
    normalized_findings = _normalize_findings(findings)
    waf = score_well_architected(normalized_findings)

    return {
        "engine": "scenario_lab",
        "architecture_source": architecture_source,
        "architecture": architecture,
        "graph": {
            "nodes": graph.number_of_nodes(),
            "edges": graph.number_of_edges(),
        },
        "scenario": scenario,
        "result": result,
        "findings": normalized_findings,
        "well_architected": waf,
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
