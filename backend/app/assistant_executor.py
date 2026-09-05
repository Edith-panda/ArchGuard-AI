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


# Local conversation fallback for the current single-user development workspace.
# It keeps the last grounded architecture so short follow-ups do not collapse to
# a one-node graph. Production deployment should replace this with session-scoped
# persistence (Redis/DB) rather than process memory.
_LAST_ARCHITECTURE: Optional[dict] = None
_LAST_FINDINGS: list[dict] = []


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
    if not architecture or not architecture.get("services"):
        raise AssistantExecutionError("Architecture is required for this operation.")
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
    return bool(lower in {"postgresql", "postgres", "kafka", "redis"} or any(
        token in lower for token in (" service", " client", " gateway", " database", " db")
    ))


def _architecture_from_prompt(prompt: str) -> Optional[dict]:
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
                "evidence": [{"filename": "conversation-prompt", "reason": "Explicitly described in the user prompt"}],
            }
        return services[key]["name"]

    def add_connection(source: str, target: str):
        src, dst = add_service(source), add_service(target)
        if src and dst and src != dst:
            connections.add((src, dst))

    for sentence in re.split(r"[\n.!?]", prompt):
        if "→" in sentence or "->" in sentence:
            parts = [_clean_component_name(p) for p in re.split(r"\s*(?:→|->)\s*", sentence)]
            parts = [p for p in parts if _looks_like_component(p)]
            for source, target in zip(parts, parts[1:]):
                add_connection(source, target)

    component_pattern = re.compile(
        r"\b([A-Z][A-Za-z0-9-]*(?:\s+[A-Z][A-Za-z0-9-]*)*\s+(?:Service|Client|Gateway|Database|DB))\b"
    )
    for match in component_pattern.finditer(prompt):
        add_service(match.group(1))
    if re.search(r"\bPostgreSQL\b", prompt, re.IGNORECASE):
        add_service("PostgreSQL")
    if re.search(r"\bKafka\b", prompt, re.IGNORECASE):
        add_service("Kafka")

    call_pattern = re.compile(
        r"([A-Z][A-Za-z0-9-]*(?:\s+[A-Z][A-Za-z0-9-]*)*\s+Service)\s+(?:synchronously\s+)?calls\s+([^.!?]+)",
        re.IGNORECASE,
    )
    for match in call_pattern.finditer(prompt):
        for target in component_pattern.findall(match.group(2)):
            add_connection(match.group(1), target)

    shared_db_pattern = re.compile(
        r"([^.!?]+?)\s+share(?:s)?\s+(?:one\s+|a\s+|the\s+)?PostgreSQL\s+database", re.IGNORECASE
    )
    for match in shared_db_pattern.finditer(prompt):
        for service_name in component_pattern.findall(match.group(1)):
            add_connection(service_name, "PostgreSQL")

    kafka_consumer_pattern = re.compile(
        r"([A-Z][A-Za-z0-9-]*(?:\s+[A-Z][A-Za-z0-9-]*)*\s+Service)\s+consumes?[^.!?]*\sfrom\s+Kafka",
        re.IGNORECASE,
    )
    for match in kafka_consumer_pattern.finditer(prompt):
        add_connection("Kafka", match.group(1))

    if not services:
        return None
    return {
        "services": list(services.values()),
        "connections": [[s, t] for s, t in sorted(connections)],
        "connection_evidence": [],
        "assumptions": ["Architecture was reconstructed conservatively from explicit relationships in the conversational prompt."],
    }


def _find_database(architecture: dict) -> Optional[str]:
    for service in architecture.get("services", []):
        name = str(service.get("name", ""))
        if str(service.get("type", "")).lower() == "database" or any(
            term in name.lower() for term in ("postgres", "mysql", "mongo", "database", " db")
        ):
            return name
    return None


def _find_named_component(prompt: str, architecture: dict) -> Optional[str]:
    text = prompt.lower()
    candidates = sorted((str(s.get("name", "")) for s in architecture.get("services", [])), key=len, reverse=True)
    return next((name for name in candidates if name and name.lower() in text), None)


def detect_scenario(prompt: str, architecture: dict) -> dict:
    text = prompt.lower()
    database_failure_terms = (
        "database fails", "database failed", "database has failed", "database goes down", "database outage",
        "db fails", "db failed", "db has failed", "db goes down", "db outage",
        "postgres fails", "postgres failed", "postgres has failed", "postgres goes down", "postgres outage",
        "postgresql fails", "postgresql failed", "postgresql has failed", "postgresql goes down", "postgresql outage",
    )
    if any(term in text for term in database_failure_terms):
        return {"scenario_type": "database_failure", "target": _find_named_component(prompt, architecture) or _find_database(architecture), "traffic_multiplier": 1.0}
    if any(term in text for term in ("traffic spike", "load spike", "more traffic", "10x traffic", "30x traffic", "100x traffic")):
        match = re.search(r"(\d+(?:\.\d+)?)\s*[x×]", text)
        return {"scenario_type": "traffic_spike", "target": None, "traffic_multiplier": float(match.group(1)) if match else 10.0}
    if any(term in text for term in ("dependency fails", "dependency failure", "third party fails", "external service fails")):
        return {"scenario_type": "dependency_failure", "target": _find_named_component(prompt, architecture), "traffic_multiplier": 1.0}
    return {"scenario_type": "component_failure", "target": _find_named_component(prompt, architecture), "traffic_multiplier": 1.0}


def _remember(architecture: dict, findings: Optional[list[dict]] = None):
    global _LAST_ARCHITECTURE, _LAST_FINDINGS
    if architecture and architecture.get("services"):
        _LAST_ARCHITECTURE = architecture
    if findings is not None:
        _LAST_FINDINGS = findings


def _best_architecture(prompt: str, architecture: Optional[dict]) -> tuple[dict, str]:
    explicit = architecture if architecture and architecture.get("services") else _architecture_from_prompt(prompt)
    if explicit and len(explicit.get("services", [])) > 1:
        _remember(explicit)
        return explicit, "current_request"
    if _LAST_ARCHITECTURE and _LAST_ARCHITECTURE.get("services"):
        return _LAST_ARCHITECTURE, "conversation_context"
    if explicit:
        _remember(explicit)
        return explicit, "current_request"
    raise AssistantExecutionError("Architecture is required for this operation.")


def execute_review(architecture: dict) -> dict:
    architecture = require_architecture(architecture)
    graph = build_architecture_graph(architecture)
    findings = _normalize_findings(assign_risk_scores(analyze_architecture(architecture)))
    _remember(architecture, findings)
    return {"engine": "architecture_review", "architecture": architecture, "graph": {"nodes": graph.number_of_nodes(), "edges": graph.number_of_edges()}, "findings": findings, "well_architected": score_well_architected(findings)}


def execute_simulation(prompt: str, architecture: Optional[dict]) -> dict:
    architecture, source = _best_architecture(prompt, architecture)
    graph = build_architecture_graph(architecture)
    scenario = detect_scenario(prompt, architecture)
    result = run_scenario(graph=graph, scenario_type=scenario["scenario_type"], target=scenario.get("target"), traffic_multiplier=scenario.get("traffic_multiplier", 1.0))
    findings = _normalize_findings(assign_risk_scores(analyze_architecture(architecture)))
    _remember(architecture, findings)
    return {"engine": "scenario_lab", "architecture_source": source, "architecture": architecture, "graph": {"nodes": graph.number_of_nodes(), "edges": graph.number_of_edges()}, "scenario": scenario, "result": result, "findings": findings, "well_architected": score_well_architected(findings)}


def execute_assistant_intent(intent: EngineeringIntent, prompt: str, architecture: Optional[dict]) -> dict:
    if intent == EngineeringIntent.REVIEW:
        architecture, source = _best_architecture(prompt, architecture)
        result = execute_review(architecture)
        result["architecture_source"] = source
        return result
    if intent == EngineeringIntent.SIMULATE:
        return execute_simulation(prompt, architecture)
    if intent == EngineeringIntent.MODIFY:
        baseline, source = _best_architecture(prompt, architecture)
        return {"engine": "architecture_evolution", "status": "requires_reasoning", "architecture_source": source, "baseline_architecture": baseline, "previous_findings": _LAST_FINDINGS, "message": "Modify the grounded baseline architecture using the new stakeholder requirement."}
    if intent == EngineeringIntent.DESIGN:
        return {"engine": "system_design", "status": "requires_reasoning", "message": "System-design generation requires the reasoning layer."}
    if intent == EngineeringIntent.QUESTION:
        return {"engine": "architecture_qa", "status": "requires_reasoning", "baseline_architecture": _LAST_ARCHITECTURE}
    if intent == EngineeringIntent.REMEDIATE:
        baseline, source = _best_architecture(prompt, architecture)
        findings = _LAST_FINDINGS or _normalize_findings(assign_risk_scores(analyze_architecture(baseline)))
        _remember(baseline, findings)
        prioritized = sorted(findings, key=lambda f: f.get("risk_score", 0), reverse=True)[:3]
        return {"engine": "remediation", "status": "approval_required", "architecture_source": source, "baseline_architecture": baseline, "prioritized_findings": prioritized, "external_execution": False, "message": "Create proposals for these grounded findings only. Do not execute without explicit human approval."}
    raise AssistantExecutionError(f"Unsupported intent: {intent}")
